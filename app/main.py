import csv
import io
import uuid
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI()
from app.storage import connect


def parse(raw):
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        headers = reader.fieldnames
        if not headers or len(headers) != len(set(headers)):
            raise ValueError("Missing or duplicate headers")
        rows = list(reader)
        if not rows or len(rows) > 10000:
            raise ValueError("Require 1 to 10000 rows")
        if any(None in row or None in row.values() for row in rows):
            raise ValueError("Malformed CSV row")
        return {"headers": headers, "rows": rows}
    except (UnicodeError, csv.Error, ValueError) as error:
        raise HTTPException(422, str(error)) from error


class Mapping(BaseModel):
    left: dict[str, str]
    right: dict[str, str]


class Review(BaseModel):
    decision: str
    reason: str = ""


def normalize(source, mapping):
    if set(mapping) != {"transaction_id", "amount", "currency"}:
        raise HTTPException(422, "Map transaction_id, amount and currency")
    if len(set(mapping.values())) != 3 or not set(mapping.values()) <= set(source["headers"]):
        raise HTTPException(422, "Mapping must reference three distinct existing columns")
    result = defaultdict(list)
    for line, row in enumerate(source["rows"], 2):
        key = row[mapping["transaction_id"]].strip()
        currency = row[mapping["currency"]].strip().upper()
        try:
            amount = Decimal(row[mapping["amount"]])
            if not amount.is_finite() or abs(amount) > Decimal("1e15") or amount != amount.quantize(Decimal(".01")):
                raise ValueError()
        except (InvalidOperation, ValueError):
            raise HTTPException(422, f"Invalid two-decimal amount at row {line}")
        if not key or len(currency) != 3 or not currency.isascii() or not currency.isalpha():
            raise HTTPException(422, f"Invalid ID or currency at row {line}")
        result[key].append({"row": line, "amount": format(amount, ".2f"), "currency": currency})
    return result


def reconcile(left, right):
    findings = []
    for key in sorted(set(left) | set(right)):
        a, b = left.get(key, []), right.get(key, [])
        if len(a) > 1 or len(b) > 1:
            kind = "duplicate_key"
        elif not a or not b:
            kind = "missing_left" if not a else "missing_right"
        elif a[0]["currency"] != b[0]["currency"]:
            kind = "currency_mismatch"
        elif Decimal(a[0]["amount"]) != Decimal(b[0]["amount"]):
            kind = "amount_mismatch"
        else:
            continue
        findings.append({
            "finding_id": f"F{len(findings)+1:03d}", "type": kind,
            "transaction_id": key, "left": a, "right": b,
            "delta": format(Decimal(a[0]["amount"]) - Decimal(b[0]["amount"]), ".2f") if kind == "amount_mismatch" else None,
        })
    return findings


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/ready")
def ready():
    with connect() as store:
        store.db.execute("SELECT id FROM runs LIMIT 1")
    return {"status": "ready"}


@app.post("/runs", status_code=201)
async def create(left: UploadFile = File(...), right: UploadFile = File(...)):
    sources = {}
    for name, upload in (("left", left), ("right", right)):
        raw = await upload.read(1_000_001)
        if len(raw) > 1_000_000:
            raise HTTPException(413, "CSV exceeds 1 MB")
        sources[name] = parse(raw)
    run_id = str(uuid.uuid4())
    data = {"id": run_id, "state": "uploaded", "sources": sources, "mapping": None, "findings": [], "reviews": {}}
    with connect(write=True) as db:
        db.insert(run_id, data)
    return {"id": run_id}


@app.get("/runs/{run_id}")
def get_run(run_id: str):
    with connect() as db:
        return db.read(run_id)


@app.put("/runs/{run_id}/mapping")
def set_mapping(run_id: str, mapping: Mapping):
    with connect(write=True) as db:
        data = db.read(run_id)
        if data["state"] == "reconciled":
            raise HTTPException(409, "Create a new run to change reconciled inputs")
        value = mapping.model_dump()
        for side in ("left", "right"):
            normalize(data["sources"][side], value[side])
        data.update(mapping=value, state="mapped")
        db.save(run_id, data)
    return {"state": "mapped"}


@app.post("/runs/{run_id}/reconcile")
def execute(run_id: str):
    with connect(write=True) as db:
        data = db.read(run_id)
        if data["state"] == "uploaded":
            raise HTTPException(409, "Confirm mapping first")
        if data["state"] != "reconciled":
            data["findings"] = reconcile(*[normalize(data["sources"][s], data["mapping"][s]) for s in ("left", "right")])
            data["state"] = "reconciled"
            db.save(run_id, data)
    return data["findings"]


@app.put("/runs/{run_id}/reviews/{finding_id}")
def review(run_id: str, finding_id: str, value: Review):
    if value.decision not in ("accepted", "rejected"):
        raise HTTPException(422, "Decision must be accepted or rejected")
    with connect(write=True) as db:
        data = db.read(run_id)
        if finding_id not in {f["finding_id"] for f in data["findings"]}:
            raise HTTPException(404, "Finding not found")
        data["reviews"][finding_id] = value.model_dump()
        db.save(run_id, data)
    return value


@app.get("/runs/{run_id}/export")
def export(run_id: str):
    with connect() as db:
        data = db.read(run_id)
    if data["state"] != "reconciled":
        raise HTTPException(409, "Reconcile first")
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["finding_id", "type", "transaction_id", "delta", "decision"])
    for f in data["findings"]:
        # Neutralize spreadsheet formulas in user-controlled transaction IDs.
        key = f["transaction_id"]
        if key.startswith(("=", "+", "-", "@", "\t", "\r")):
            key = "'" + key
        writer.writerow([f["finding_id"], f["type"], key, f["delta"], data["reviews"].get(f["finding_id"], {}).get("decision", "pending")])
    return Response(out.getvalue(), media_type="text/csv", headers={"Content-Disposition": 'attachment; filename="reconciliation.csv"'})



@app.get("/capabilities")
def capabilities():
    from app.llm import configured
    return {"mapping_suggestions": configured()}


@app.post("/runs/{run_id}/mapping-proposal")
def mapping_proposal(run_id: str):
    from app.llm import ProposalError, propose
    with connect() as db:
        data = db.read(run_id)
    if data["state"] == "reconciled":
        raise HTTPException(409, "This run is already reconciled")
    headers = {side: data["sources"][side]["headers"] for side in ("left", "right")}
    try:
        result = propose(headers)
    except ProposalError as error:
        with connect(write=True) as db:
            current = db.read(run_id)
            current["last_proposal_error"] = error.code
            db.save(run_id, current)
        raise HTTPException(503 if error.code == "not_configured" else 502,
                            "Suggestions unavailable (" + error.code + "). Select columns manually.")
    with connect(write=True) as db:
        current = db.read(run_id)
        if current["state"] == "reconciled":
            raise HTTPException(409, "Run reconciled while proposal was pending")
        current["mapping_proposal"] = result
        current.pop("last_proposal_error", None)
        db.save(run_id, current)
    return result

# Mount last so API routes keep their existing ownership.
from fastapi.staticfiles import StaticFiles
app.mount("/", StaticFiles(directory=Path(__file__).parent / "static", html=True), name="ui")
