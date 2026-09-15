"""Failure diagnostics must be useful without revealing credentials."""
import contextlib
import io
import os
import unittest
from unittest.mock import patch
import psycopg
from scripts.init_db import initialize


class DatabaseDiagnosticsTest(unittest.TestCase):
    def run_failure(self, url, error=None):
        output = io.StringIO()
        with patch.dict(os.environ, {"DATABASE_URL": url}), contextlib.redirect_stderr(output):
            with patch("scripts.init_db.psycopg.connect", side_effect=error) as connect:
                code = initialize()
        self.assertNotEqual(code, 0)
        self.assertNotIn("private-password", output.getvalue())
        self.assertNotIn("private-host", output.getvalue())
        return output.getvalue(), connect.called

    def test_project_api_url_does_not_attempt_database_connection(self):
        out, called = self.run_failure("https://private-host.supabase.co")
        self.assertIn("PostgreSQL URI", out)
        self.assertFalse(called)

    def test_placeholder_does_not_attempt_database_connection(self):
        out, called = self.run_failure("postgresql://postgres:%5BYOUR-PASSWORD%5D@private-host/postgres")
        self.assertIn("placeholder", out)
        self.assertFalse(called)

    def test_authentication_failure_is_classified_without_raw_error(self):
        out, called = self.run_failure(
            "postgresql://postgres:private-password@private-host/postgres",
            psycopg.OperationalError("password authentication failed: private-password at private-host"))
        self.assertTrue(called)
        self.assertIn("authentication_failed", out)

    def test_ipv6_network_failure_is_distinguished(self):
        out, _ = self.run_failure(
            "postgresql://postgres:private-password@private-host/postgres",
            psycopg.OperationalError("private-host: Network is unreachable"))
        self.assertIn("network_unreachable_use_ipv4_pooler", out)
