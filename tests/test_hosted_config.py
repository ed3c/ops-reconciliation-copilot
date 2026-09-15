import os
import unittest
from unittest.mock import patch
from fastapi import HTTPException
from app.storage import connect


class HostedConfigTest(unittest.TestCase):
    def test_hosted_requests_cannot_fall_back_to_local_sqlite(self):
        with patch.dict(os.environ, {"VERCEL": "1", "DATABASE_URL": ""}):
            with self.assertRaises(HTTPException) as caught:
                with connect():
                    self.fail("Hosted storage silently used SQLite")
        self.assertEqual(caught.exception.status_code, 503)
