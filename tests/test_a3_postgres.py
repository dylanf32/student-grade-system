"""
Tests for A3 — PostgreSQL storage backend.

Uses unittest.mock to simulate psycopg2 so no live database is required.
Covers:
  - ImportError when psycopg2 is absent
  - setup_schema() creates all six tables
  - save() / load() happy path (students)
  - save() returns False and rolls back on DB error
  - save_dataset() happy path (students + classes + enrollments + categories + grades)
  - save_dataset() returns False and rolls back on DB error
  - load_dataset() returns empty payload on DB error
  - Credentials are not logged in error messages (_redact helper)
  - _add_connect_timeout helper behaviour
  - _redact helper does not expose passwords
"""

from __future__ import annotations

import json
import sys
import types
import uuid
from unittest.mock import MagicMock, patch, call
from typing import List

import pytest

from app.models.student import Student, CourseGrade
from app.storage.postgres_storage import (
    _add_connect_timeout,
    _redact,
    _student_to_row,
    _row_to_student,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_student(name: str = "Alice", grade: float = 85.0) -> Student:
    return Student(name=name, grade=grade)


def _make_psycopg2_mock():
    """Return a minimal psycopg2 mock with connect(), cursor(), and context manager."""
    pg = MagicMock()

    conn = MagicMock()
    cur = MagicMock()

    # cursor() returns the mock cursor
    conn.cursor.return_value = cur

    # Context manager protocol for `with conn:` — used by save/save_dataset
    conn.__enter__ = MagicMock(return_value=conn)
    conn.__exit__ = MagicMock(return_value=False)

    pg.connect.return_value = conn
    # Expose OperationalError so PostgresStorage can reference it
    pg.OperationalError = Exception

    return pg, conn, cur


# ---------------------------------------------------------------------------
# _add_connect_timeout
# ---------------------------------------------------------------------------

class TestAddConnectTimeout:
    def test_url_style_no_query(self):
        url = "postgresql://user:pass@host/db"
        result = _add_connect_timeout(url, 5)
        assert "connect_timeout=5" in result
        assert result.startswith("postgresql://")

    def test_url_style_existing_query(self):
        url = "postgresql://user:pass@host/db?sslmode=require"
        result = _add_connect_timeout(url, 3)
        assert "connect_timeout=3" in result
        assert "?" in result
        assert result.count("?") == 1

    def test_keyword_style(self):
        url = "host=localhost dbname=test user=u password=p"
        result = _add_connect_timeout(url, 10)
        assert "connect_timeout=10" in result

    def test_already_present_unchanged(self):
        url = "postgresql://host/db?connect_timeout=7"
        assert _add_connect_timeout(url, 5) == url

    def test_postgres_scheme(self):
        url = "postgres://host/db"
        result = _add_connect_timeout(url, 5)
        assert "connect_timeout=5" in result


# ---------------------------------------------------------------------------
# _redact
# ---------------------------------------------------------------------------

class TestRedact:
    def test_url_credentials_removed(self):
        msg = "could not connect: postgresql://admin:s3cr3t@db.example.com/prod"
        result = _redact(msg)
        assert "s3cr3t" not in result
        assert "admin" not in result
        assert "<redacted>" in result

    def test_keyword_password_removed(self):
        msg = "FATAL: password=hunter2 authentication failed"
        result = _redact(msg)
        assert "hunter2" not in result
        assert "<redacted>" in result

    def test_safe_message_unchanged(self):
        msg = "relation \"students\" does not exist"
        assert _redact(msg) == msg


# ---------------------------------------------------------------------------
# ImportError path (psycopg2 absent)
# ---------------------------------------------------------------------------

class TestImportError:
    def test_constructor_raises_import_error_when_no_psycopg2(self):
        """If psycopg2 is unavailable, PostgresStorage raises ImportError."""
        with patch("app.storage.postgres_storage._HAS_PSYCOPG2", False):
            from app.storage.postgres_storage import PostgresStorage
            with pytest.raises(ImportError, match="psycopg2"):
                PostgresStorage("postgresql://host/db")

    def test_setup_schema_raises_import_error_when_no_psycopg2(self):
        with patch("app.storage.postgres_storage._HAS_PSYCOPG2", False):
            from app.storage.postgres_storage import PostgresStorage
            with pytest.raises(ImportError, match="psycopg2"):
                PostgresStorage.setup_schema("postgresql://host/db")


# ---------------------------------------------------------------------------
# setup_schema
# ---------------------------------------------------------------------------

class TestSetupSchema:
    def test_creates_all_tables(self):
        pg_mock, _conn_mock, _cur_mock = _make_psycopg2_mock()
        # setup_schema opens its own connection, so model a plain connect()
        conn_local = MagicMock()
        cur_local = MagicMock()
        # `with conn.cursor() as cur:` uses the cursor's context manager protocol
        cur_local.__enter__ = MagicMock(return_value=cur_local)
        cur_local.__exit__ = MagicMock(return_value=False)
        conn_local.cursor.return_value = cur_local
        conn_local.__enter__ = MagicMock(return_value=conn_local)
        conn_local.__exit__ = MagicMock(return_value=False)
        # Both __init__ and setup_schema call psycopg2.connect(); return conn_local for both
        pg_mock.connect.return_value = conn_local

        with patch("app.storage.postgres_storage.psycopg2", pg_mock), \
             patch("app.storage.postgres_storage._HAS_PSYCOPG2", True):
            from app.storage.postgres_storage import PostgresStorage
            PostgresStorage.setup_schema("postgresql://host/db")

        # DDL was executed on the cursor returned by the context manager
        assert cur_local.execute.called
        ddl_call = cur_local.execute.call_args[0][0]
        for table in ("students", "classes", "enrollments", "categories",
                      "assignments", "enrollment_grades"):
            assert table in ddl_call

        # Connection was closed
        conn_local.close.assert_called_once()


# ---------------------------------------------------------------------------
# save / load — students only
# ---------------------------------------------------------------------------

class TestSaveLoad:
    def _make_storage(self):
        pg_mock, conn_mock, cur_mock = _make_psycopg2_mock()
        with patch("app.storage.postgres_storage.psycopg2", pg_mock), \
             patch("app.storage.postgres_storage._HAS_PSYCOPG2", True):
            from app.storage.postgres_storage import PostgresStorage
            storage = PostgresStorage("postgresql://host/db")
        return storage, conn_mock, cur_mock

    def test_save_returns_true_on_success(self):
        storage, conn_mock, cur_mock = self._make_storage()
        students = [_make_student()]
        result = storage.save(students)
        assert result is True

    def test_save_calls_upsert(self):
        storage, conn_mock, cur_mock = self._make_storage()
        students = [_make_student("Bob", 72.0)]
        storage.save(students)
        # execute must have been called at least for DELETE and INSERT
        assert cur_mock.execute.call_count >= 2

    def test_save_returns_false_on_db_error(self):
        storage, conn_mock, cur_mock = self._make_storage()
        cur_mock.execute.side_effect = Exception("connection reset")
        result = storage.save([_make_student()])
        assert result is False

    def test_save_rollback_on_error(self):
        """Context manager __exit__ is called with the exception — psycopg2 rolls back."""
        storage, conn_mock, cur_mock = self._make_storage()
        cur_mock.execute.side_effect = Exception("disk full")
        storage.save([_make_student()])
        # __exit__ was called (context manager protocol honoured)
        assert conn_mock.__exit__.called

    def test_load_delegates_to_load_dataset(self):
        storage, conn_mock, cur_mock = self._make_storage()
        # fetchall for each SELECT: students, classes, enrollments, categories, eg
        cur_mock.fetchall.side_effect = [
            # students row
            [("abc", "Alice", 85.0, "a@b.c", "CS", "Junior", 3.5,
              "[]", "notes", "", "", "[]")],
            [],  # classes
            [],  # enrollments
            [],  # categories
            [],  # enrollment_grades
        ]
        result = storage.load()
        assert len(result) == 1
        assert result[0].name == "Alice"

    def test_load_returns_empty_on_error(self):
        storage, conn_mock, cur_mock = self._make_storage()
        cur_mock.execute.side_effect = Exception("table not found")
        result = storage.load()
        assert result == []

    def test_save_empty_list_deletes_all(self):
        storage, conn_mock, cur_mock = self._make_storage()
        result = storage.save([])
        assert result is True
        # First execute call should be the unconditional DELETE
        first_sql = cur_mock.execute.call_args_list[0][0][0]
        assert "DELETE FROM students" in first_sql

    def test_no_credentials_in_error_log(self, caplog):
        import logging
        storage, conn_mock, cur_mock = self._make_storage()
        # Inject a fake URL fragment into the error message
        cur_mock.execute.side_effect = Exception(
            "postgresql://admin:mysecret@db/prod connection refused"
        )
        with caplog.at_level(logging.ERROR, logger="app.storage.postgres_storage"):
            storage.save([_make_student()])
        for record in caplog.records:
            assert "mysecret" not in record.getMessage()


# ---------------------------------------------------------------------------
# save_dataset / load_dataset
# ---------------------------------------------------------------------------

class TestSaveDataset:
    def _make_storage(self):
        pg_mock, conn_mock, cur_mock = _make_psycopg2_mock()
        with patch("app.storage.postgres_storage.psycopg2", pg_mock), \
             patch("app.storage.postgres_storage._HAS_PSYCOPG2", True):
            from app.storage.postgres_storage import PostgresStorage
            storage = PostgresStorage("postgresql://host/db")
        return storage, conn_mock, cur_mock

    def _class_dict(self, cls_id: str | None = None) -> dict:
        return {"id": cls_id or str(uuid.uuid4()), "code": "CS101", "title": "Intro"}

    def _enrollment_dict(self, sid: str, cls_id: str) -> dict:
        return {
            "id": str(uuid.uuid4()),
            "student_id": sid,
            "class_id": cls_id,
        }

    def test_returns_true_on_success(self):
        storage, conn_mock, cur_mock = self._make_storage()
        s = _make_student()
        cls = self._class_dict()
        enroll = self._enrollment_dict(s.id, cls["id"])
        result = storage.save_dataset([s], [cls], [enroll])
        assert result is True

    def test_returns_false_on_db_error(self):
        storage, conn_mock, cur_mock = self._make_storage()
        cur_mock.execute.side_effect = Exception("FK violation")
        result = storage.save_dataset([_make_student()], [], [])
        assert result is False

    def test_rollback_on_error(self):
        storage, conn_mock, cur_mock = self._make_storage()
        cur_mock.execute.side_effect = Exception("disk full")
        storage.save_dataset([_make_student()], [], [])
        assert conn_mock.__exit__.called

    def test_empty_dataset_succeeds(self):
        storage, conn_mock, cur_mock = self._make_storage()
        result = storage.save_dataset([], [], [])
        assert result is True

    def test_load_dataset_returns_empty_payload_on_error(self):
        storage, conn_mock, cur_mock = self._make_storage()
        cur_mock.execute.side_effect = Exception("relation not found")
        payload = storage.load_dataset()
        assert payload.students == []
        assert payload.classes == []
        assert payload.enrollments == []

    def test_load_dataset_happy_path(self):
        storage, conn_mock, cur_mock = self._make_storage()
        cls_id = str(uuid.uuid4())
        cls_dict = {"id": cls_id, "code": "CS101"}
        enroll_dict = {"id": str(uuid.uuid4()), "student_id": "s1", "class_id": cls_id}
        cur_mock.fetchall.side_effect = [
            [("s1", "Alice", 90.0, "", "", "", None, "[]", "", "", "", "[]")],
            [(json.dumps(cls_dict),)],
            [(json.dumps(enroll_dict),)],
            [],  # categories
            [],  # enrollment_grades
        ]
        payload = storage.load_dataset()
        assert len(payload.students) == 1
        assert payload.students[0].name == "Alice"
        assert payload.classes[0]["code"] == "CS101"
        assert len(payload.enrollments) == 1

    def test_categories_and_grades_persisted(self):
        """Categories with assignments and enrollment grades are upserted."""
        storage, conn_mock, cur_mock = self._make_storage()
        s = _make_student()
        cls = self._class_dict()
        enroll = self._enrollment_dict(s.id, cls["id"])
        cat = {
            "id": str(uuid.uuid4()),
            "class_id": cls["id"],
            "name": "Homework",
            "weight": 40.0,
            "assignments": [
                {"id": str(uuid.uuid4()), "name": "HW1", "possible": 100}
            ],
        }
        eg = {
            "id": str(uuid.uuid4()),
            "enrollment_id": enroll["id"],
            "assignment_id": cat["assignments"][0]["id"],
            "score": 85.0,
        }
        result = storage.save_dataset([s], [cls], [enroll], [cat], [eg])
        assert result is True
        # Verify assignment upsert was attempted
        all_sql = " ".join(
            str(c[0][0]) for c in cur_mock.execute.call_args_list if c[0]
        )
        assert "assignments" in all_sql
        assert "enrollment_grades" in all_sql


# ---------------------------------------------------------------------------
# _student_to_row / _row_to_student round-trip
# ---------------------------------------------------------------------------

class TestStudentSerialization:
    def test_round_trip(self):
        s = Student(
            name="Carol",
            grade=78.5,
            email="c@school.edu",
            major="Math",
            academic_year="Sophomore",
            gpa=3.1,
            courses=[CourseGrade("Calculus", 82.0)],
            notes="Good student",
            linkedin_url="https://linkedin.com/in/carol",
            department="Sciences",
            groups=["Honors"],
        )
        row = _student_to_row(s)
        assert row["id"] == s.id
        assert json.loads(row["courses"])[0]["course"] == "Calculus"

        # Simulate what PostgreSQL would return (tuple)
        raw_courses = json.loads(row["courses"])
        raw_groups = json.loads(row["groups"])
        pg_row = (
            row["id"], row["name"], row["grade"], row["email"], row["major"],
            row["academic_year"], row["gpa"], json.dumps(raw_courses),
            row["notes"], row["linkedin_url"], row["department"],
            json.dumps(raw_groups),
        )
        restored = _row_to_student(pg_row)
        assert restored.name == s.name
        assert restored.grade == s.grade
        assert restored.gpa == s.gpa
        assert restored.courses[0].course == "Calculus"
        assert restored.groups == ["Honors"]

    def test_null_gpa_preserved(self):
        s = Student(name="Dave", grade=55.0)
        row = _student_to_row(s)
        assert row["gpa"] is None
        pg_row = (
            row["id"], row["name"], row["grade"], "", "", "", None,
            "[]", "", "", "", "[]",
        )
        restored = _row_to_student(pg_row)
        assert restored.gpa is None

    def test_malformed_course_skipped(self):
        """A malformed course dict in the courses JSON is silently skipped."""
        pg_row = (
            str(uuid.uuid4()), "Eve", 60.0, "", "", "", None,
            json.dumps([{"bad": "data"}]),  # missing "course" key
            "", "", "", "[]",
        )
        # Should not raise
        student = _row_to_student(pg_row)
        assert student.courses == []
