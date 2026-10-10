"""
A5 — PostgreSQL connection UI: route tests.

Covers:
- Routes absent when LOCAL_DEMO_MODE is False (default)
- /api/pg/test and /api/pg/connect return 403 from non-loopback
- /api/pg/test: bad URL, empty URL, connection failure (mocked) — secrets not in response
- /api/pg/connect: failed connection keeps previous backend; secret-free error response
- /api/config exposes local_demo flag
"""

import importlib
import sys
import types
import unittest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers to build a test Flask client with LOCAL_DEMO_MODE toggled
# ---------------------------------------------------------------------------

def _make_app(local_demo: bool):
    """Import run_web with LOCAL_DEMO_MODE forced to *local_demo*.

    Each call uses a fresh import so the module-level `if LOCAL_DEMO_MODE:`
    block is re-evaluated.
    """
    # Patch the config flag before importing run_web
    import app.config as cfg
    original = cfg.LOCAL_DEMO_MODE
    cfg.LOCAL_DEMO_MODE = local_demo

    # Force re-import of run_web so the `if LOCAL_DEMO_MODE:` block is re-run
    if "run_web" in sys.modules:
        del sys.modules["run_web"]

    import run_web as rw
    flask_app = rw.app
    flask_app.config["TESTING"] = True
    client = flask_app.test_client()

    # Restore config for other tests
    cfg.LOCAL_DEMO_MODE = original
    return flask_app, client, rw


# ---------------------------------------------------------------------------
# Tests — routes disabled when LOCAL_DEMO_MODE is False
# ---------------------------------------------------------------------------

class TestPgRoutesDisabledByDefault(unittest.TestCase):
    """Routes must not exist when LOCAL_DEMO_MODE is False."""

    def setUp(self):
        self.app, self.client, _ = _make_app(local_demo=False)

    def test_pg_test_route_absent(self):
        r = self.client.post(
            "/api/pg/test",
            json={"url": "postgresql://localhost/test"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(r.status_code, 404)

    def test_pg_connect_route_absent(self):
        r = self.client.post(
            "/api/pg/connect",
            json={"url": "postgresql://localhost/test"},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(r.status_code, 404)

    def test_config_local_demo_false(self):
        r = self.client.get("/api/config")
        self.assertEqual(r.status_code, 200)
        data = r.get_json()
        self.assertFalse(data.get("local_demo"))


# ---------------------------------------------------------------------------
# Tests — routes enabled in local-demo mode
# ---------------------------------------------------------------------------

class TestPgRoutesLocalDemo(unittest.TestCase):
    """Routes exist and respect loopback guard in LOCAL_DEMO_MODE."""

    def setUp(self):
        self.app, self.client, _ = _make_app(local_demo=True)

    def _post_test(self, url, remote="127.0.0.1"):
        return self.client.post(
            "/api/pg/test",
            json={"url": url},
            environ_base={"REMOTE_ADDR": remote},
        )

    def _post_connect(self, url, remote="127.0.0.1"):
        return self.client.post(
            "/api/pg/connect",
            json={"url": url},
            environ_base={"REMOTE_ADDR": remote},
        )

    # ── config flag ──────────────────────────────────────────────────────────

    def test_config_local_demo_true(self):
        r = self.client.get("/api/config")
        data = r.get_json()
        self.assertTrue(data.get("local_demo"))

    # ── loopback guard ───────────────────────────────────────────────────────

    def test_pg_test_non_loopback_rejected(self):
        r = self._post_test("postgresql://localhost/test", remote="203.0.113.1")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(r.get_json().get("success"))

    def test_pg_connect_non_loopback_rejected(self):
        r = self._post_connect("postgresql://localhost/test", remote="203.0.113.1")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(r.get_json().get("success"))

    # ── input validation ─────────────────────────────────────────────────────

    def test_pg_test_empty_url(self):
        r = self.client.post(
            "/api/pg/test",
            json={"url": ""},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(r.status_code, 400)
        self.assertFalse(r.get_json().get("success"))

    def test_pg_test_bad_scheme(self):
        r = self._post_test("mysql://localhost/test")
        self.assertEqual(r.status_code, 400)
        data = r.get_json()
        self.assertFalse(data.get("success"))

    def test_pg_test_missing_url_key(self):
        r = self.client.post(
            "/api/pg/test",
            json={},
            environ_base={"REMOTE_ADDR": "127.0.0.1"},
        )
        self.assertEqual(r.status_code, 400)

    # ── failed connection — secret-free response ──────────────────────────────

    def test_pg_test_connection_failure_no_credentials_in_response(self):
        """A failed connection must not echo credentials back to the client.

        When psycopg2 is absent (typical CI), the route returns a static 503
        message with no user-supplied data — the URL is never reflected back.
        When psycopg2 is present, _redact() strips credentials before logging
        and the response carries only a sanitised driver message.
        """
        secret_url = "postgresql://secretuser:s3cr3tpass@pg.internal:5432/mydb"
        r = self._post_test(secret_url)
        # Must be a 503 (driver absent or connection refused) — never 200
        self.assertEqual(r.status_code, 503)
        data = r.get_json()
        self.assertFalse(data.get("success"))
        error_text = data.get("error", "")
        # The raw password must not appear in the response
        self.assertNotIn("s3cr3tpass", error_text)
        # The raw username must not appear in plain form alongside a password
        # (acceptable to see "secretuser" only if password is redacted, which
        # is the case — but easiest to verify the password alone)

    def test_pg_connect_failure_keeps_previous_backend(self):
        """A failed pg/connect must not switch the manager's storage backend."""
        import run_web
        manager = run_web.manager
        original_storage = manager._storage

        failing_url = "postgresql://user:badpass@pg.example:5432/db"
        r = self._post_connect(failing_url)

        self.assertIn(r.status_code, (503,))
        self.assertFalse(r.get_json().get("success"))
        # Storage must be unchanged after failed connect
        self.assertIs(manager._storage, original_storage)

    def test_pg_connect_failure_secret_free_response(self):
        """Error message from pg/connect must not contain the password."""
        secret_url = "postgresql://admin:hunter2@pg.internal/mydb"
        r = self._post_connect(secret_url)
        # 503 — driver absent or connection refused
        self.assertEqual(r.status_code, 503)
        error_text = r.get_json().get("error", "")
        self.assertNotIn("hunter2", error_text)

    def test_pg_test_postgres_scheme_accepted(self):
        """'postgres://' (short form) must also be accepted as a valid scheme."""
        r = self._post_test("postgres://localhost/test")
        # 503 (connection failed / driver absent), not 400 (bad scheme)
        self.assertEqual(r.status_code, 503)


if __name__ == "__main__":
    unittest.main()
