"""
Tests for A4 — Explicit JSON import to PostgreSQL.

Covers:
  - Backup is written before any database work
  - Round-trip: all entity types inserted with correct counts
  - UUID collision: existing rows are skipped (DO NOTHING), counts reported
  - Failed import rolls back completely (no partial state)
  - Missing JSON file returns False without backup or DB access
  - Failed backup aborts before touching the database
  - Credentials not logged on failure
  - Legacy JSON formats (v1 bare array, v2 object) load transparently
  - Import with categories and enrollment_grades
  - Empty JSON file (no entities) succeeds with zero counts
  - Failed rollback on connection.rollback() error does not mask original failure

No live database is required: psycopg2.connect is mocked throughout.
"""

from __future__ import annotations

import json
import logging
import os
import sys
import uuid
from typing import Any, Dict, List
from unittest.mock import MagicMock, call, patch

import pytest

# Ensure project root is on path
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from scripts.import_json_to_postgres import (
    import_json_to_postgres,
    _backup_json,
    _load_json_payload,
    _redact,
)
from app.models.student import Student


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_v3_json(tmp_path, students=None, classes=None, enrollments=None,
                  categories=None, enrollment_grades=None):
    """Write a v3 JSON file to *tmp_path* and return the file path."""
    payload = {
        "version": 3,
        "students": students or [],
        "classes": classes or [],
        "enrollments": enrollments or [],
        "categories": categories or [],
        "enrollment_grades": enrollment_grades or [],
    }
    p = str(tmp_path / "students.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(payload, fh)
    return p


def _make_student_dict(name="Alice", grade=85.0) -> dict:
    s = Student(name=name, grade=grade)
    return s.to_dict()


def _make_conn_mock(rowcount=1):
    """Return (conn_mock, cur_mock) where execute succeeds and rowcount=1."""
    conn = MagicMock()
    cur = MagicMock()
    cur.rowcount = rowcount
    conn.cursor.return_value = cur
    return conn, cur


# ---------------------------------------------------------------------------
# _redact helper
# ---------------------------------------------------------------------------

class TestRedact:
    def test_url_credentials_redacted(self):
        msg = "postgresql://admin:secret@host/db connection refused"
        result = _redact(msg)
        assert "secret" not in result
        assert "admin" not in result

    def test_safe_message_unchanged(self):
        msg = "relation does not exist"
        assert _redact(msg) == msg


# ---------------------------------------------------------------------------
# Backup helper
# ---------------------------------------------------------------------------

class TestBackupJson:
    def test_backup_creates_timestamped_file(self, tmp_path):
        src = tmp_path / "data.json"
        src.write_text('{"version":3}')
        backup = _backup_json(str(src))
        assert os.path.exists(backup)
        assert backup.startswith(str(src))
        assert "backup_" in backup

    def test_backup_content_matches_source(self, tmp_path):
        src = tmp_path / "data.json"
        src.write_text('{"key":"value"}')
        backup = _backup_json(str(src))
        with open(backup) as f:
            assert f.read() == '{"key":"value"}'

    def test_missing_source_raises(self, tmp_path):
        with pytest.raises(OSError):
            _backup_json(str(tmp_path / "nonexistent.json"))


# ---------------------------------------------------------------------------
# _load_json_payload — format transparency
# ---------------------------------------------------------------------------

class TestLoadJsonPayload:
    def test_v3_loads_all_entities(self, tmp_path):
        s = _make_student_dict()
        cls_id = str(uuid.uuid4())
        enroll_id = str(uuid.uuid4())
        path = _make_v3_json(
            tmp_path,
            students=[s],
            classes=[{"id": cls_id, "code": "CS101", "title": "Intro"}],
            enrollments=[{"id": enroll_id, "student_id": s["id"], "class_id": cls_id}],
        )
        data = _load_json_payload(path)
        assert len(data["students"]) == 1
        assert len(data["classes"]) == 1
        assert len(data["enrollments"]) == 1
        assert data["students"][0]["name"] == "Alice"

    def test_v1_bare_array_loads_students(self, tmp_path):
        """v1 bare array yields students and empty collections."""
        s = _make_student_dict()
        p = str(tmp_path / "v1.json")
        with open(p, "w") as fh:
            json.dump([s], fh)
        data = _load_json_payload(p)
        assert len(data["students"]) == 1
        assert data["classes"] == []
        assert data["enrollments"] == []

    def test_v2_object_loads_students_and_classes(self, tmp_path):
        s = _make_student_dict()
        cls_id = str(uuid.uuid4())
        payload = {
            "version": 2,
            "students": [s],
            "classes": [{"id": cls_id, "code": "CS201", "title": "Data Structures"}],
            "enrollments": [{"id": str(uuid.uuid4()), "student_id": s["id"],
                             "class_id": cls_id}],
        }
        p = str(tmp_path / "v2.json")
        with open(p, "w") as fh:
            json.dump(payload, fh)
        data = _load_json_payload(p)
        assert len(data["students"]) == 1
        assert len(data["classes"]) == 1


# ---------------------------------------------------------------------------
# import_json_to_postgres — main function
# ---------------------------------------------------------------------------

class TestImportJsonToPostgres:
    """All tests mock psycopg2.connect; no live database needed."""

    def _patch_connect(self, conn_mock):
        """Patch psycopg2 (set to a mock module) and mark _HAS_PSYCOPG2=True."""
        import contextlib
        pg_mock = MagicMock()
        pg_mock.connect.return_value = conn_mock

        @contextlib.contextmanager
        def _ctx():
            with patch("scripts.import_json_to_postgres.psycopg2", pg_mock), \
                 patch("scripts.import_json_to_postgres._HAS_PSYCOPG2", True):
                yield

        return _ctx()

    # ── Happy path: round-trip ───────────────────────────────────────────────

    def test_returns_true_on_success(self, tmp_path):
        s = _make_student_dict()
        path = _make_v3_json(tmp_path, students=[s])
        conn, cur = _make_conn_mock(rowcount=1)
        with self._patch_connect(conn):
            result = import_json_to_postgres(path, "postgresql://host/db")
        assert result is True

    def test_commit_called_on_success(self, tmp_path):
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock(rowcount=1)
        with self._patch_connect(conn):
            import_json_to_postgres(path, "postgresql://host/db")
        conn.commit.assert_called_once()

    def test_connection_closed_on_success(self, tmp_path):
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock(rowcount=1)
        with self._patch_connect(conn):
            import_json_to_postgres(path, "postgresql://host/db")
        conn.close.assert_called_once()

    def test_backup_written_before_db_access(self, tmp_path):
        """The backup must exist before psycopg2.connect is called."""
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        backup_created_before_connect = []

        pg_mock = MagicMock()

        def fake_connect(url):
            existing = [f for f in os.listdir(tmp_path) if "backup_" in f]
            backup_created_before_connect.append(len(existing) > 0)
            conn, _ = _make_conn_mock()
            return conn

        pg_mock.connect.side_effect = fake_connect
        with patch("scripts.import_json_to_postgres.psycopg2", pg_mock), \
             patch("scripts.import_json_to_postgres._HAS_PSYCOPG2", True):
            import_json_to_postgres(path, "postgresql://host/db")

        assert backup_created_before_connect == [True]

    # ── Entity counts and SQL calls ──────────────────────────────────────────

    def test_all_entity_types_inserted(self, tmp_path):
        s = _make_student_dict()
        cls_id = str(uuid.uuid4())
        enroll_id = str(uuid.uuid4())
        cat_id = str(uuid.uuid4())
        asgn_id = str(uuid.uuid4())
        eg_id = str(uuid.uuid4())
        categories = [{
            "id": cat_id, "class_id": cls_id, "name": "HW", "weight": 100.0,
            "assignments": [{"id": asgn_id, "name": "HW1", "possible": 10}],
        }]
        enrollment_grades = [{
            "id": eg_id, "enrollment_id": enroll_id,
            "assignment_id": asgn_id, "score": 9.0,
        }]
        path = _make_v3_json(
            tmp_path,
            students=[s],
            classes=[{"id": cls_id, "code": "CS101", "title": "Intro"}],
            enrollments=[{"id": enroll_id, "student_id": s["id"], "class_id": cls_id}],
            categories=categories,
            enrollment_grades=enrollment_grades,
        )
        conn, cur = _make_conn_mock(rowcount=1)
        with self._patch_connect(conn):
            result = import_json_to_postgres(path, "postgresql://host/db")
        assert result is True
        all_sql = " ".join(str(c[0][0]) for c in cur.execute.call_args_list if c[0])
        for table in ("students", "classes", "enrollments", "categories",
                      "assignments", "enrollment_grades"):
            assert table in all_sql

    def test_empty_json_succeeds_with_zero_inserts(self, tmp_path):
        path = _make_v3_json(tmp_path)
        conn, cur = _make_conn_mock(rowcount=0)
        with self._patch_connect(conn):
            result = import_json_to_postgres(path, "postgresql://host/db")
        assert result is True
        # No execute calls needed for zero entities (cursor never called for INSERT)
        conn.commit.assert_called_once()

    # ── UUID collision: DO NOTHING ───────────────────────────────────────────

    def test_existing_uuid_skipped_not_overwritten(self, tmp_path, caplog):
        """rowcount=0 means the row was skipped (DO NOTHING)."""
        s = _make_student_dict()
        path = _make_v3_json(tmp_path, students=[s])
        conn, cur = _make_conn_mock(rowcount=0)  # simulate existing UUID
        with self._patch_connect(conn):
            with caplog.at_level(logging.INFO,
                                 logger="scripts.import_json_to_postgres"):
                result = import_json_to_postgres(path, "postgresql://host/db")
        assert result is True
        # The "skipped" count must appear in the log
        log_text = " ".join(r.getMessage() for r in caplog.records)
        assert "skipped=1" in log_text

    # ── Failed import rolls back ─────────────────────────────────────────────

    def test_returns_false_on_db_error(self, tmp_path):
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock()
        cur.execute.side_effect = Exception("FK violation")
        with self._patch_connect(conn):
            result = import_json_to_postgres(path, "postgresql://host/db")
        assert result is False

    def test_rollback_called_on_db_error(self, tmp_path):
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock()
        cur.execute.side_effect = Exception("disk full")
        with self._patch_connect(conn):
            import_json_to_postgres(path, "postgresql://host/db")
        conn.rollback.assert_called_once()

    def test_connection_closed_on_error(self, tmp_path):
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock()
        cur.execute.side_effect = Exception("connection reset")
        with self._patch_connect(conn):
            import_json_to_postgres(path, "postgresql://host/db")
        conn.close.assert_called_once()

    def test_commit_not_called_on_error(self, tmp_path):
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock()
        cur.execute.side_effect = Exception("error")
        with self._patch_connect(conn):
            import_json_to_postgres(path, "postgresql://host/db")
        conn.commit.assert_not_called()

    def test_rollback_error_does_not_mask_original_failure(self, tmp_path):
        """Even if rollback itself raises, the function returns False cleanly."""
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock()
        cur.execute.side_effect = Exception("original error")
        conn.rollback.side_effect = Exception("rollback error")
        with self._patch_connect(conn):
            result = import_json_to_postgres(path, "postgresql://host/db")
        assert result is False

    # ── Error cases: missing file, failed backup ─────────────────────────────

    def test_missing_json_file_returns_false(self, tmp_path):
        conn, _ = _make_conn_mock()
        with self._patch_connect(conn):
            result = import_json_to_postgres(
                str(tmp_path / "nonexistent.json"), "postgresql://host/db"
            )
        assert result is False
        conn.cursor.assert_not_called()  # DB never touched

    def test_failed_backup_aborts_before_db(self, tmp_path):
        """If shutil.copy2 raises, the DB must not be touched."""
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock()
        with self._patch_connect(conn):
            with patch("scripts.import_json_to_postgres.shutil.copy2",
                       side_effect=OSError("no space")):
                result = import_json_to_postgres(path, "postgresql://host/db")
        assert result is False
        conn.cursor.assert_not_called()

    # ── Credential safety ────────────────────────────────────────────────────

    def test_no_credentials_in_log_on_error(self, tmp_path, caplog):
        path = _make_v3_json(tmp_path, students=[_make_student_dict()])
        conn, cur = _make_conn_mock()
        cur.execute.side_effect = Exception(
            "postgresql://admin:topsecret@db/prod connection refused"
        )
        with self._patch_connect(conn):
            with caplog.at_level(logging.ERROR,
                                 logger="scripts.import_json_to_postgres"):
                import_json_to_postgres(path, "postgresql://host/db")
        for record in caplog.records:
            assert "topsecret" not in record.getMessage()
            assert "admin" not in record.getMessage()
