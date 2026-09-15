"""GIS popup credential exchange. No client secret or redirect callback required."""
import secrets

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.access import (CHALLENGE_SECONDS, authenticate, clear_cookie, identity,
                        serializer, set_cookie, settings)

router = APIRouter()


class Credential(BaseModel):
    credential: str = Field(min_length=1, max_length=16384)


@router.get("/auth/config")
def config(request: Request):
    client, _, _ = settings()
    nonce = secrets.token_urlsafe(32)
    response = JSONResponse({"client_id": client, "nonce": nonce})
    set_cookie(response, request, "challenge",
               serializer("owner-challenge-v1").dumps(nonce), CHALLENGE_SECONDS)
    return response


@router.post("/auth/google")
def sign_in(request: Request, value: Credential):
    try:
        owner = authenticate(request, value.credential)
        response = JSONResponse({"signed_in": True})
        import time
        set_cookie(response, request, "session",
                   serializer("owner-session-v1").dumps(owner), owner["exp"] - int(time.time()))
    except HTTPException as error:
        response = JSONResponse({"detail": error.detail}, error.status_code)
        clear_cookie(response, request, "session")
    clear_cookie(response, request, "challenge")
    return response


@router.get("/auth/me")
def me(request: Request):
    owner = identity(request)
    return {"email": owner["email"], "sub": owner["sub"]}


@router.post("/auth/logout")
def logout(request: Request):
    response = JSONResponse({"signed_in": False})
    clear_cookie(response, request, "session")
    clear_cookie(response, request, "challenge")
    return response
