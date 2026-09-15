import os
import tempfile
import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException
from starlette.requests import Request
from starlette.responses import Response

from app.access import identity, serializer, set_cookie, verify_google_credential
from scripts.auth_test_support import CLIENT, EMAIL, SECRET, keys, token


class GoogleAccessTest(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {"VERCEL": "1", "GOOGLE_CLIENT_ID": CLIENT,
            "OWNER_GOOGLE_EMAIL": EMAIL, "OWNER_GOOGLE_SUB": "", "AUTH_SESSION_SECRET": SECRET})
        self.env.start()
        self.addCleanup(self.env.stop)

    def request(self, value):
        return Request({"type": "http", "method": "GET", "scheme": "https", "path": "/runs/x",
                        "server": ("example.test", 443), "query_string": b"",
                        "headers": [(b"cookie", ("__Host-recon_session=" + value).encode())]})

    def session(self, **overrides):
        value = {"aud": CLIENT, "email": EMAIL, "sub": "owner-sub", "exp": int(time.time()) + 300}
        value.update(overrides)
        return serializer("owner-session-v1").dumps(value)

    def assert_status(self, status, action):
        with self.assertRaises(HTTPException) as error:
            action()
        self.assertEqual(error.exception.status_code, status)

    def test_session_integrity_expiry_and_current_allowlist(self):
        cookie = self.session()
        self.assertEqual(identity(self.request(cookie))["sub"], "owner-sub")
        self.assert_status(401, lambda: identity(self.request(cookie + "tampered")))
        self.assert_status(401, lambda: identity(self.request(self.session(exp=1))))
        self.assert_status(401, lambda: identity(self.request(self.session(aud="other-client"))))
        self.assert_status(403, lambda: identity(self.request(self.session(email="other@gmail.com"))))
        with patch.dict(os.environ, {"OWNER_GOOGLE_EMAIL": "new-owner@gmail.com"}):
            self.assert_status(403, lambda: identity(self.request(cookie)))
        with patch.dict(os.environ, {"OWNER_GOOGLE_SUB": "different-sub"}):
            self.assert_status(403, lambda: identity(self.request(cookie)))
        with patch.dict(os.environ, {"AUTH_SESSION_SECRET": SECRET + "-rotated"}):
            self.assert_status(401, lambda: identity(self.request(cookie)))

    def test_hosted_cookie_flags_and_missing_config(self):
        response = Response()
        set_cookie(response, self.request(""), "session", "value", 300)
        header = response.headers["set-cookie"]
        for part in ("__Host-recon_session=", "HttpOnly", "Secure", "SameSite=lax", "Path=/"):
            self.assertIn(part, header)
        self.assertNotIn("Domain=", header)
        with patch.dict(os.environ, {"GOOGLE_CLIENT_ID": ""}):
            self.assert_status(503, lambda: identity(self.request("")))

    def test_sdk_rejects_correctly_shaped_token_signed_by_wrong_key(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            key, public = keys(a)
            impostor, _ = keys(b)
            with patch("google.oauth2.id_token._fetch_certs", return_value={
                    "test-key": public.read_text()}):
                self.assertEqual(verify_google_credential(token(key, "nonce"), CLIENT)["email"], EMAIL)
                self.assert_status(401, lambda: verify_google_credential(token(impostor, "nonce"), CLIENT))
