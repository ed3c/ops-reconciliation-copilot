const $ = (id) => document.getElementById(id);
let run;
const transactionFields = ["transaction_id", "amount", "currency"];
const batchFields = {left: ["batch_id", "payment_id", "amount", "currency"], right: ["batch_id", "amount", "currency"]};
let suggestionsConfigured = false;
const fieldsFor = (side) => run.mode === "batch" ? batchFields[side] : transactionFields;
function modeNotes() {
  const batch = $("mode").value === "batch";
  $("mode-note").textContent = batch
    ? "Left: positive expected payments. Right: one positive bank deposit per explicit batch reference. Fees, refunds and inferred matches are outside this comparison."
    : "Compare one transaction ID on each side.";
  $("mapping-note").textContent = batch
    ? "Map batch ID, payment ID, amount and currency on the left; batch ID, amount and currency on the right. Confirm each source column."
    : "Choose the transaction ID, amount and currency in each file. IDs are matched exactly.";
  $("suggest").hidden = !suggestionsConfigured || batch;
}
$("mode").addEventListener("change", modeNotes);
async function api(path, method = "GET", body) {
  const options = {method, headers: {"X-Recon-Request": "1"}};
  if (body instanceof FormData) options.body = body;
  else if (body !== undefined) {
    options.headers["Content-Type"] = "application/json";
    options.body = JSON.stringify(body);
  }
  const response = await fetch(path, options);
  if (response.status === 401) {
    location.reload();
    throw new Error("Session expired. Sign in again.");
  }
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail));
  return data;
}
async function action(button, work) {
  $("error").textContent = "";
  $("notice").textContent = "";
  button.disabled = true;
  try { await work(); }
  catch (error) { $("error").textContent = error.message; }
  finally { button.disabled = false; }
}
function node(tag, text, parent) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (parent) parent.append(element);
  return element;
}
async function refresh() {
  run = await api("/runs/" + encodeURIComponent(run.id));
  $("mode").value = run.mode || "transaction";
  modeNotes();
  $("mapping-panel").hidden = run.state === "reconciled";
  $("columns").replaceChildren();
  for (const side of ["left", "right"]) {
    const group = node("div", undefined, $("columns"));
    node("h3", side === "left" ? "Left file" : "Right file", group);
    for (const field of fieldsFor(side)) {
      const label = node("label", side + " " + field, group);
      const select = node("select", undefined, label);
      select.id = side + "-" + field;
      select.setAttribute("aria-label", side + " " + field);
      node("option", "Choose a column", select).value = "";
      for (const header of run.sources[side].headers) node("option", header, select).value = header;
      select.value = run.mapping?.[side]?.[field] || "";
      select.required = true;
    }
  }
  $("results").hidden = run.state !== "reconciled";
  if (run.state !== "reconciled") return;
  $("summary").textContent = (run.mode === "batch" ? (run.matched_batches?.length || 0) + " matched batches · " : "")
    + run.findings.length + " differences found";
  $("export").href = "/runs/" + encodeURIComponent(run.id) + "/export";
  $("findings").replaceChildren();
  for (const finding of run.findings) {
    const card = node("article", undefined, $("findings"));
    card.className = "finding";
    node("h3", finding.finding_id + " · " + (finding.batch_id || finding.transaction_id), card);
    node("p", finding.type + (finding.delta !== null ? " · Difference: " + finding.delta : ""), card);
    const sources = node("div", "Left: " + JSON.stringify(finding.left) + "\nRight: " + JSON.stringify(finding.right), card);
    sources.className = "sources";
    const form = node("form", undefined, card);
    const label = node("label", "Decision " + finding.finding_id, form);
    const decision = node("select", undefined, label);
    for (const value of ["accepted", "rejected"]) node("option", value, decision).value = value;
    const reasonLabel = node("label", "Reason " + finding.finding_id, form);
    const reason = node("textarea", undefined, reasonLabel);
    const saved = run.reviews[finding.finding_id];
    decision.value = saved?.decision || "accepted";
    reason.value = saved?.reason || "";
    node("p", saved ? "Saved: " + saved.decision : "Pending review", form);
    const button = node("button", "Save review " + finding.finding_id, form);
    form.addEventListener("submit", event => {
      event.preventDefault();
      action(button, async () => {
        await api("/runs/" + run.id + "/reviews/" + finding.finding_id, "PUT", {decision: decision.value, reason: reason.value});
        await refresh();
        $("notice").textContent = "Review saved";
      });
    });
  }
}
$("upload").addEventListener("submit", event => {
  event.preventDefault();
  action(event.submitter, async () => {
    run = await api("/runs?mode=" + encodeURIComponent($("mode").value), "POST", new FormData(event.target));
    $("suggestion-note").textContent = "";
    history.replaceState(null, "", "?run=" + encodeURIComponent(run.id));
    await refresh();
    $("notice").textContent = "Files uploaded. Confirm the columns below.";
  });
});
$("mapping").addEventListener("submit", event => {
  event.preventDefault();
  action(event.submitter, async () => {
    const mapping = {};
    for (const side of ["left", "right"]) mapping[side] = Object.fromEntries(fieldsFor(side).map(field => [field, $(side + "-" + field).value]));
    await api("/runs/" + run.id + "/mapping", "PUT", mapping);
    await api("/runs/" + run.id + "/reconcile", "POST");
    await refresh();
    $("notice").textContent = "Reconciliation complete";
  });
});
const id = new URLSearchParams(location.search).get("run");
document.getElementById("logout").addEventListener("click", async () => {
  try {
    await api("/auth/logout", "POST");
    location.replace("/workspace");
  } catch (error) { $("error").textContent = error.message; }
});
if (id) {
  run = {id};
  refresh().catch(error => { $("error").textContent = error.message; });
}

api("/capabilities").then(value => {
  suggestionsConfigured = value.mapping_suggestions;
  modeNotes();
}).catch(() => {});
$("suggest").addEventListener("click", event => {
  const runId = run.id;
  action(event.currentTarget, async () => {
    const result = await api("/runs/" + runId + "/mapping-proposal", "POST");
    if (run.id !== runId) return;
    const proposal = result.proposal;
    if (proposal.status === "clarify") {
      $("suggestion-note").textContent = proposal.question;
      return;
    }
    for (const side of ["left", "right"]) for (const field of fieldsFor(side)) {
      $(side + "-" + field).value = proposal.mapping[side][field];
    }
    $("suggestion-note").textContent = "Suggested columns are ready. Check them before confirming.";
  });
});
