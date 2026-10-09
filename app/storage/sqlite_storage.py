"""
SQLite storage backend.

Implements BaseStorage using Python's built-in sqlite3 module.
No external dependencies required beyond the stdlib.

Schema history:
    v1 — initial: id, name, grade, email, major, academic_year, gpa, courses, notes
    v2 — added:   linkedin_url, department, groups (JSON blob)
"""

import json
import sqlite3
from typing import List

from app.models.student import Student, CourseGrade
from app.storage.base_storage import BaseStorage

_SCHEMA_VERSION = 2


class SqliteStorage(BaseStorage):
    """Persists student data to a local SQLite database.

    A single connection is kept open for the lifetime of the instance.
    This is the correct pattern for an in-process storage object — it
    avoids the cost of re-opening the file on every operation, and it
    is required for ":memory:" databases (where each new connect()
    call creates a *different* empty database).

    Attributes:
        _db_path (str):              Path to the SQLite database file.
        _conn    (sqlite3.Connection): Persistent connection.
    """

    def __init__(self, db_path: str) -> None:
        """Initialise the SQLite backend and ensure the schema exists.

        Args:
            db_path: File-system path for the SQLite database file.
                     Use ":memory:" for an in-memory database (tests).
        """
        self._db_path: str = db_path
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        if db_path != ":memory:":
            self._conn.execute("PRAGMA journal_mode=WAL;")
        self._conn.execute("PRAGMA foreign_keys=ON;")
        self._init_schema()

    # ── Schema ───────────────────────────────────────────────────────────

    def _init_schema(self) -> None:
        """Create the students table and run any pending column migrations."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id            TEXT PRIMARY KEY,
                name          TEXT NOT NULL,
                grade         REAL NOT NULL,
                email         TEXT NOT NULL DEFAULT '',
                major         TEXT NOT NULL DEFAULT '',
                academic_year TEXT NOT NULL DEFAULT '',
                gpa           REAL,
                courses       TEXT NOT NULL DEFAULT '[]',
                notes         TEXT NOT NULL DEFAULT '',
                linkedin_url  TEXT NOT NULL DEFAULT '',
                department    TEXT NOT NULL DEFAULT '',
                groups        TEXT NOT NULL DEFAULT '[]'
            )
        """)
        self._conn.commit()
        # Migrate pre-existing databases that are missing the v2 columns.
        self._add_column_if_missing("linkedin_url", "TEXT NOT NULL DEFAULT ''")
        self._add_column_if_missing("department",   "TEXT NOT NULL DEFAULT ''")
        self._add_column_if_missing("groups",       "TEXT NOT NULL DEFAULT '[]'")

    def _add_column_if_missing(self, column: str, definition: str) -> None:
        """Add a column to the students table if it does not already exist."""
        existing = {
            row[1]
            for row in self._conn.execute("PRAGMA table_info(students)").fetchall()
        }
        if column not in existing:
            self._conn.execute(
                f"ALTER TABLE students ADD COLUMN {column} {definition}"
            )
            self._conn.commit()

    # ── Serialization helpers ─────────────────────────────────────────────

    @staticmethod
    def _student_to_row(s: Student) -> dict:
        return {
            "id":            s.id,
            "name":          s.name,
            "grade":         s.grade,
            "email":         s.email,
            "major":         s.major,
            "academic_year": s.academic_year,
            "gpa":           s.gpa,
            "courses":       json.dumps([c.to_dict() for c in s.courses]),
            "notes":         s.notes,
            "linkedin_url":  s.linkedin_url,
            "department":    s.department,
            "groups":        json.dumps(s.groups),
        }

    @staticmethod
    def _row_to_student(row: sqlite3.Row) -> Student:
        raw_courses = json.loads(row["courses"] or "[]")
        courses: List[CourseGrade] = []
        for c in raw_courses:
            try:
                courses.append(CourseGrade.from_dict(c))
            except (KeyError, ValueError):
                pass

        raw_groups = json.loads(row["groups"] or "[]")
        groups = [g for g in raw_groups if isinstance(g, str)]

        return Student(
            name=row["name"],
            grade=row["grade"],
            student_id=row["id"],
            email=row["email"] or "",
            major=row["major"] or "",
            academic_year=row["academic_year"] or "",
            gpa=row["gpa"],
            courses=courses,
            notes=row["notes"] or "",
            linkedin_url=row["linkedin_url"] or "",
            department=row["department"] or "",
            groups=groups,
        )

    # ── BaseStorage Implementation ────────────────────────────────────────

    def save(self, students: List[Student]) -> bool:
        """Replace the entire students table with the given list (atomic).

        Uses a single transaction: DELETE all rows then INSERT the full
        snapshot, so a crash mid-way leaves the database unchanged
        (SQLite rolls back the transaction automatically).

        Args:
            students: Complete list of Student objects to persist.

        Returns:
            True on success, False on failure.
        """
        try:
            with self._conn:
                self._conn.execute("DELETE FROM students")
                self._conn.executemany(
                    """
                    INSERT INTO students
                        (id, name, grade, email, major, academic_year, gpa,
                         courses, notes, linkedin_url, department, groups)
                    VALUES
                        (:id, :name, :grade, :email, :major, :academic_year, :gpa,
                         :courses, :notes, :linkedin_url, :department, :groups)
                    """,
                    [self._student_to_row(s) for s in students],
                )
            return True
        except Exception as exc:
            print(f"  [SqliteStorage Error] Could not save: {exc}")
            return False

    def load(self) -> List[Student]:
        """Reads all students from the database in insertion order.

        Returns:
            List of Student objects, or empty list on failure.
        """
        try:
            rows = self._conn.execute(
                "SELECT id, name, grade, email, major, academic_year, gpa, "
                "courses, notes, linkedin_url, department, groups "
                "FROM students"
            ).fetchall()
            return [self._row_to_student(r) for r in rows]
        except Exception as exc:
            print(f"  [SqliteStorage Error] Could not load: {exc}")
            return []
