"""Owner-only API boundary. Public pages never query runs or invoke a model."""
import base64
import binascii
import os
import secrets
from urllib.parse import urlsplit

from starlette.requests import Request
from starlette.responses import JSONResponse

PUBLIC = {"/", "/index.html", "/styles.css", "/app.js", "/health", "/showcase.csv"}
PRIVATE_HEADERS = {"Cache-Control": "private, no-store", "Vary": "Authorization"}


class OwnerAccess:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return
        request = Request(scope)
        public = request.method in {"GET", "HEAD"} and request.url.path in PUBLIC
        if public:
            await self.app(scope, receive, send)
            return

        async def private_send(message):
            if message["type"] == "http.response.start":
                message = dict(message)
                headers = [(k, v) for k, v in message.get("headers", [])
                           if k.lower() not in {b"cache-control", b"vary"}]
                message["headers"] = headers + [
                    (b"cache-control", b"private, no-store"), (b"vary", b"Authorization")]
            await send(message)

        password = os.environ.get("RECON_OWNER_PASSWORD", "")
        # Unconfigured development without a provider remains available locally.
        protected = bool(password or os.environ.get("VERCEL") or os.environ.get("OPENROUTER_API_KEY"))
        if protected:
            if len(password) < 32:
                response = JSONResponse(
                    {"detail": "Owner access is not configured"}, 503, headers=PRIVATE_HEADERS)
                await response(scope, receive, send)
                return
            username, supplied = b"", b""
            try:
                scheme, token = request.headers.get("authorization", "").split(" ", 1)
                if scheme.lower() == "basic" and len(token) <= 8192:
                    username, supplied = base64.b64decode(token, validate=True).split(b":", 1)
            except (ValueError, binascii.Error):
                pass
            user_ok = secrets.compare_digest(username, b"owner")
            password_ok = secrets.compare_digest(supplied, password.encode("utf-8"))
            if not (user_ok and password_ok):
                response = JSONResponse({"detail": "Owner sign-in required"}, 401, headers={
                    **PRIVATE_HEADERS, "WWW-Authenticate": 'Basic realm="Owner workspace", charset="UTF-8"'})
                await response(scope, receive, send)
                return
            if request.method not in {"GET", "HEAD", "OPTIONS"}:
                origin = request.headers.get("origin")
                cross_site = request.headers.get("sec-fetch-site") == "cross-site"
                if (request.headers.get("x-recon-request") != "1" or cross_site
                        or (origin and urlsplit(origin).netloc != request.url.netloc)):
                    response = JSONResponse({"detail": "Same-origin owner request required"},
                                            403, headers=PRIVATE_HEADERS)
                    await response(scope, receive, send)
                    return
        await self.app(scope, receive, private_send)
