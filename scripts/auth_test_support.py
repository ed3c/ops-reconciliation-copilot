"""Local test issuer only. No Google account or production bypass."""
import os
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from google.auth import crypt, jwt

CLIENT = "test-client.apps.googleusercontent.com"
EMAIL = "owner.test@gmail.com"
SECRET = "ci-only-signing-secret-never-use-in-production"


def keys(directory):
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    key = Path(directory) / "test-private.pem"
    public = Path(directory) / "test-public.pem"
    key.write_bytes(private.private_bytes(serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))
    public.write_bytes(private.public_key().public_bytes(serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo))
    return key, public


def token(key, nonce, **overrides):
    now = int(time.time())
    claims = {"iss": "https://accounts.google.com", "aud": CLIENT, "sub": "test-owner-id",
              "email": EMAIL, "email_verified": True, "iat": now - 1,
              "exp": now + 3600, "nonce": nonce}
    claims.update(overrides)
    return jwt.encode(crypt.RSASigner.from_string(Path(key).read_bytes(), key_id="test-key"),
                      claims).decode()


def environment(public):
    return {"GOOGLE_CLIENT_ID": CLIENT, "OWNER_GOOGLE_EMAIL": EMAIL,
            "AUTH_SESSION_SECRET": SECRET, "OWNER_GOOGLE_SUB": "",
            "AUTH_TEST_PUBLIC_KEY": str(public), "RECON_OWNER_PASSWORD": "", "VERCEL": ""}


def app_factory():
    # Inject only test public-key retrieval. Real SDK signature/claim verification runs.
    # This factory is never imported by the production entry point app.main:app.
    from google.oauth2 import id_token
    public = Path(os.environ["AUTH_TEST_PUBLIC_KEY"]).read_text()
    id_token._fetch_certs = lambda request, certs_url: {"test-key": public}
    from app.main import app
    return app
