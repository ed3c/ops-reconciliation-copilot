"""Google owner authentication and a default-deny private API boundary."""
import hashlib
import os
import secrets
import time
from urllib.parse import urlsplit

from fastapi import HTTPException, Request
from itsdangerous import BadData, URLSafeTimedSerializer
from starlette.responses import JSONResponse

PUBLIC = {"/", "/index.html", "/styles.css", "/app.js", "/health", "/showcase.csv",
          "/login.js"}
NO_STORE = {"Cache-Control": "private, no-store", "Vary": "Cookie"}
SESSION_SECONDS = 3600
CHALLENGE_SECONDS = 600


def protected():
    return any(os.environ.get(key) for key in (
        "VERCEL", "OPENROUTER_API_KEY", "GOOGLE_CLIENT_ID", "OWNER_GOOGLE_EMAIL",
        "OWNER_GOOGLE_SUB", "AUTH_SESSION_SECRET", "RECON_OWNER_PASSWORD"))


def settings():
    client = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
    email = os.environ.get("OWNER_GOOGLE_EMAIL", "").strip().lower()
    secret = os.environ.get("AUTH_SESSION_SECRET", "")
    if (not client.endswith(".apps.googleusercontent.com")
            or not email.endswith("@gmail.com") or email.count("@") != 1
            or len(email) <= len("@gmail.com") or len(secret) < 32):
        raise HTTPException(503, "Google owner sign-in is not configured")
    return client, email, secret


def serializer(salt):
    return URLSafeTimedSerializer(settings()[2], salt=salt,
                                  signer_kwargs={"digest_method": hashlib.sha256})


def secure(request):
    return bool(os.environ.get("VERCEL")) or request.url.scheme == "https"


def cookie_name(request, kind):
    return ("__Host-" if secure(request) else "") + "recon_" + kind


def set_cookie(response, request, kind, value, seconds):
    response.set_cookie(cookie_name(request, kind), value, max_age=seconds,
                        httponly=True, secure=secure(request), samesite="lax", path="/")


def clear_cookie(response, request, kind):
    response.delete_cookie(cookie_name(request, kind), path="/", secure=secure(request),
                           httponly=True, samesite="lax")


def same_origin(request):
    origin = request.headers.get("origin")
    try:
        invalid_origin = origin and (
            urlsplit(origin).scheme not in {"http", "https"}
            or urlsplit(origin).netloc != request.url.netloc)
    except ValueError:
        invalid_origin = True
    if (request.headers.get("x-recon-request") != "1" or invalid_origin
            or request.headers.get("sec-fetch-site") == "cross-site"):
        raise HTTPException(403, "Same-origin request required")


def owner_allowed(email, sub):
    expected = settings()[1]
    pinned = os.environ.get("OWNER_GOOGLE_SUB", "").strip()
    if (not isinstance(email, str) or email.lower() != expected
            or not isinstance(sub, str) or not sub
            or (pinned and not secrets.compare_digest(sub.encode(), pinned.encode()))):
        raise HTTPException(403, "This Google account is not allowed")


def identity(request):
    if not protected():
        return {"sub": "local-development", "email": None}
    client, _, _ = settings()
    raw = request.cookies.get(cookie_name(request, "session"), "")
    try:
        if len(raw) > 4096:
            raise ValueError()
        value = serializer("owner-session-v1").loads(raw, max_age=SESSION_SECONDS)
        if (not isinstance(value, dict) or value.get("aud") != client
                or type(value.get("exp")) is not int or value["exp"] <= int(time.time())):
            raise ValueError()
    except (BadData, ValueError, TypeError):
        raise HTTPException(401, "Google sign-in required")
    # Re-check current allowlist on every request, including reads and exports.
    owner_allowed(value.get("email"), value.get("sub"))
    return value


def verify_google_credential(credential, client):
    from google.auth.exceptions import GoogleAuthError, TransportError
    from google.auth.transport.requests import Request as GoogleRequest
    from google.oauth2 import id_token

    transport = GoogleRequest()

    def bounded_request(*args, **kwargs):
        kwargs["timeout"] = 5
        return transport(*args, **kwargs)

    try:
        # Official verifier checks Google's signature, audience, issuer and time.
        return id_token.verify_oauth2_token(credential, bounded_request, audience=client)
    except TransportError as error:
        raise HTTPException(503, "Google verification temporarily unavailable") from error
    except (GoogleAuthError, ValueError, TypeError, KeyError) as error:
        raise HTTPException(401, "Invalid Google credential") from error


def authenticate(request, credential):
    client, _, _ = settings()
    try:
        raw = request.cookies.get(cookie_name(request, "challenge"), "")
        challenge = serializer("owner-challenge-v1").loads(raw, max_age=CHALLENGE_SECONDS)
        if not isinstance(challenge, str) or not challenge:
            raise ValueError()
    except (BadData, ValueError):
        raise HTTPException(403, "Sign-in challenge expired; reload and try again")
    value = verify_google_credential(credential, client)
    nonce = value.get("nonce")
    if not isinstance(nonce, str) or not secrets.compare_digest(nonce.encode(), challenge.encode()):
        raise HTTPException(403, "Sign-in challenge mismatch")
    if (value.get("email_verified") is not True or value.get("aud") != client
            or value.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}
            or type(value.get("exp")) is not int or value["exp"] <= int(time.time())):
        raise HTTPException(401, "Invalid Google credential")
    owner_allowed(value.get("email"), value.get("sub"))
    return {"sub": value["sub"], "email": value["email"].lower(), "aud": client,
            "exp": min(value["exp"], int(time.time()) + SESSION_SECONDS)}


class OwnerAccess:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        path, method = request.url.path, request.method
        if method in {"GET", "HEAD"} and path in PUBLIC:
            await self.app(scope, receive, send)
            return

        async def private_send(message):
            if message["type"] == "http.response.start":
                message = dict(message)
                headers = [(k, v) for k, v in message.get("headers", [])
                           if k.lower() not in {b"cache-control", b"vary"}]
                message["headers"] = headers + [(b"cache-control", b"private, no-store"),
                    (b"vary", b"Cookie"), (b"x-frame-options", b"DENY"),
                    (b"cross-origin-opener-policy", b"same-origin-allow-popups")]
            await send(message)

        try:
            login_read = method == "GET" and path in {"/workspace", "/auth/config"}
            login_write = method == "POST" and path in {"/auth/google", "/auth/logout"}
            if not (login_read or login_write):
                request.scope.setdefault("state", {})["owner"] = identity(request)
            if method not in {"GET", "HEAD", "OPTIONS"} and (protected() or login_write):
                same_origin(request)
        except HTTPException as error:
            await JSONResponse({"detail": error.detail}, error.status_code,
                               headers=NO_STORE)(scope, receive, send)
            return
        await self.app(scope, receive, private_send)
