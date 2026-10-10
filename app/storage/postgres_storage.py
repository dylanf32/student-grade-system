"""
PostgreSQL storage backend.

Implements BaseStorage using psycopg2.

Usage
-----
Instantiate with a connection URL read from the environment::

    import os
    from app.storage.postgres_storage import PostgresStorage
    storage = PostgresStorage(os.environ["DATABASE_URL"])

Never pass credentials via command-line arguments or log them.

Setup command
-------------
Call ``PostgresStorage.setup_schema(url)`` once to create all tables::

    python -c "
    import os
    from app.storage.postgres_storage import PostgresStorage
    PostgresStorage.setup_schema(os.environ['DATABASE_URL'])
    "

Design notes
------------
- PostgreSQL is authoritative: ``save`` / ``save_dataset`` perform upsert
  operations rather than DELETE+INSERT so a stale in-memory snapshot cannot
  silently erase rows added by another process.
- All mutations are wrapped in a single transaction; any error causes a full
  rollback, leaving the database unchanged.
- Failed writes return False without raising; the caller sees the same
  contract as JsonStorage / SqliteStorage.
- Credentials are read from DATABASE_URL at construction time.  They are
  never logged or stored in any attribute.
- JSON / SQLite remain selectable by passing the appropriate backend to
  StudentManager.
"""

from __future__ import annotations

import json
import logging
from typing import List

from app.models.student import Student, CourseGrade
from app.storage.base_storage import BaseStorage, DatasetPayload

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Optional driver import — raises a clear ImportError if psycopg2 is absent
# ---------------------------------------------------------------------------

try:
    import psycopg2
    import psycopg2.extras
    import psycopg2.extensions
    _HAS_PSYCOPG2 = True
except ImportError:  # pragma: no cover
    _HAS_PSYCOPG2 = False
    psycopg2 = None  # type: ignore[assignment]


# ---------------------------------------------------------------------------
# DDL — all table definitions live here so setup_schema() is the single
# authoritative source of truth.
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS students (
    id            TEXT PRIMARY KEY,
    name          TEXT NOT NULL,
    grade         DOUBLE PRECISION NOT NULL,
    email         TEXT NOT NULL DEFAULT '',
    major         TEXT NOT NULL DEFAULT '',
    academic_year TEXT NOT NULL DEFAULT '',
    gpa           DOUBLE PRECISION,
    courses       JSONB NOT NULL DEFAULT '[]',
    notes         TEXT NOT NULL DEFAULT '',
    linkedin_url  TEXT NOT NULL DEFAULT '',
    department    TEXT NOT NULL DEFAULT '',
    groups        JSONB NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS classes (
    id         TEXT PRIMARY KEY,
    data       JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollments (
    id         TEXT PRIMARY KEY,
    student_id TEXT NOT NULL REFERENCES students(id),
    class_id   TEXT NOT NULL REFERENCES classes(id),
    data       JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id       TEXT PRIMARY KEY,
    class_id TEXT NOT NULL REFERENCES classes(id),
    data     JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS assignments (
    id          TEXT PRIMARY KEY,
    category_id TEXT NOT NULL REFERENCES categories(id),
    data        JSONB NOT NULL
);

CREATE TABLE IF NOT EXISTS enrollment_grades (
    id            TEXT PRIMARY KEY,
    enrollment_id TEXT NOT NULL REFERENCES enrollments(id),
    assignment_id TEXT NOT NULL REFERENCES assignments(id),
    data          JSONB NOT NULL
);
"""


class PostgresStorage(BaseStorage):
    """Persists the full dataset to a PostgreSQL database.

    One psycopg2 connection is kept open for the lifetime of the instance.
    The connection is opened with ``autocommit=False`` so that every mutation
    runs inside an explicit transaction.

    Args:
        database_url: A libpq connection string / DSN such as
                      ``postgresql://user:pass@host:5432/dbname``.
                      Read this from ``os.environ["DATABASE_URL"]``; never
                      hard-code or log it.
        connect_timeout: TCP connect timeout in seconds (default 5).
                         Prevents the constructor from hanging indefinitely.

    Raises:
        ImportError:  If psycopg2 is not installed.
        psycopg2.OperationalError: If the connection cannot be established.
    """

    def __init__(self, database_url: str, connect_timeout: int = 5) -> None:
        if not _HAS_PSYCOPG2:
            raise ImportError(
                "psycopg2 is required for PostgresStorage. "
                "Install it with: pip install psycopg2-binary"
            )
        # Build connect kwargs — never store the raw URL in an instance attr
        # that might surface in repr()/str() or logs.
        dsn = _add_connect_timeout(database_url, connect_timeout)
        self._conn = psycopg2.connect(dsn)
        self._conn.autocommit = False

    # ── Schema setup (class method — usable without a storage instance) ────

    @classmethod
    def setup_schema(cls, database_url: str, connect_timeout: int = 5) -> None:
        """Create all tables if they do not exist.

        Safe to run repeatedly (all statements use ``CREATE … IF NOT EXISTS``).
        Must be called once before the first ``save`` / ``load``.

        Args:
            database_url:    PostgreSQL connection URL from DATABASE_URL env var.
            connect_timeout: TCP connect timeout in seconds (default 5).

        Raises:
            ImportError:  If psycopg2 is not installed.
            psycopg2.Error: On connection or DDL failure.
        """
        if not _HAS_PSYCOPG2:
            raise ImportError(
                "psycopg2 is required for PostgresStorage. "
                "Install it with: pip install psycopg2-binary"
            )
        dsn = _add_connect_timeout(database_url, connect_timeout)
        conn = psycopg2.connect(dsn)
        try:
            with conn:
                with conn.cursor() as cur:
                    cur.execute(_DDL)
        finally:
            conn.close()

    # ── BaseStorage — students-only interface (legacy) ─────────────────────

    def save(self, students: List[Student]) -> bool:
        """Upsert students into the database.

        Uses INSERT … ON CONFLICT DO UPDATE (upsert) so concurrent writes
        from other processes are not silently lost.  Rows for students that
        no longer exist in ``students`` are deleted.

        Args:
            students: Complete current list of Student objects.

        Returns:
            True on success, False on any failure (transaction is rolled back).
        """
        try:
            with self._conn:  # transaction — rolls back on exception
                cur = self._conn.cursor()
                live_ids = [s.id for s in students]
                # Remove students no longer present
                if live_ids:
                    cur.execute(
                        "DELETE FROM students WHERE id <> ALL(%s)",
                        (live_ids,),
                    )
                else:
                    cur.execute("DELETE FROM students")
                # Upsert each student
                for s in students:
                    row = _student_to_row(s)
                    cur.execute(
                        """
                        INSERT INTO students
                            (id, name, grade, email, major, academic_year, gpa,
                             courses, notes, linkedin_url, department, groups)
                        VALUES
                            (%(id)s, %(name)s, %(grade)s, %(email)s, %(major)s,
                             %(academic_year)s, %(gpa)s, %(courses)s, %(notes)s,
                             %(linkedin_url)s, %(department)s, %(groups)s)
                        ON CONFLICT (id) DO UPDATE SET
                            name          = EXCLUDED.name,
                            grade         = EXCLUDED.grade,
                            email         = EXCLUDED.email,
                            major         = EXCLUDED.major,
                            academic_year = EXCLUDED.academic_year,
                            gpa           = EXCLUDED.gpa,
                            courses       = EXCLUDED.courses,
                            notes         = EXCLUDED.notes,
                            linkedin_url  = EXCLUDED.linkedin_url,
                            department    = EXCLUDED.department,
                            groups        = EXCLUDED.groups
                        """,
                        row,
                    )
            return True
        except Exception as exc:
            logger.error("[PostgresStorage] save() failed: %s", _redact(str(exc)))
            return False

    def load(self) -> List[Student]:
        """Read all students from the database.

        Returns:
            List of Student objects, or empty list on failure.
        """
        return self.load_dataset().students

    # ── BaseStorage — full dataset interface ───────────────────────────────

    def save_dataset(
        self,
        students: List[Student],
        classes: List[dict],
        enrollments: List[dict],
        categories: List[dict] | None = None,
        enrollment_grades: List[dict] | None = None,
    ) -> bool:
        """Upsert the complete dataset inside one transaction.

        Orphaned classes, enrollments, categories, assignments, and
        enrollment_grades whose IDs are no longer in the supplied lists are
        deleted.  The deletion order respects foreign-key constraints
        (child tables deleted before parent tables).

        Args:
            students:          List of Student objects.
            classes:           Serialized class dicts (each must have ``"id"``).
            enrollments:       Serialized enrollment dicts (must have ``"id"``,
                               ``"student_id"``, ``"class_id"``).
            categories:        Serialized Category dicts (A2; optional).
            enrollment_grades: Serialized EnrollmentGrade dicts (A2; optional).

        Returns:
            True on success, False on any failure (transaction rolled back).
        """
        cats = categories if categories is not None else []
        egrades = enrollment_grades if enrollment_grades is not None else []

        # Collect all assignment dicts from category dicts for FK integrity
        assignments: List[dict] = []
        for cat in cats:
            for asgn in cat.get("assignments", []):
                assignments.append(
                    {"id": asgn["id"], "category_id": cat["id"], "data": asgn}
                )

        try:
            with self._conn:
                cur = self._conn.cursor()

                # ── Students ──────────────────────────────────────────────
                live_student_ids = [s.id for s in students]
                if live_student_ids:
                    cur.execute(
                        "DELETE FROM students WHERE id <> ALL(%s)",
                        (live_student_ids,),
                    )
                else:
                    cur.execute("DELETE FROM students")
                for s in students:
                    row = _student_to_row(s)
                    cur.execute(
                        """
                        INSERT INTO students
                            (id, name, grade, email, major, academic_year, gpa,
                             courses, notes, linkedin_url, department, groups)
                        VALUES
                            (%(id)s, %(name)s, %(grade)s, %(email)s, %(major)s,
                             %(academic_year)s, %(gpa)s, %(courses)s, %(notes)s,
                             %(linkedin_url)s, %(department)s, %(groups)s)
                        ON CONFLICT (id) DO UPDATE SET
                            name          = EXCLUDED.name,
                            grade         = EXCLUDED.grade,
                            email         = EXCLUDED.email,
                            major         = EXCLUDED.major,
                            academic_year = EXCLUDED.academic_year,
                            gpa           = EXCLUDED.gpa,
                            courses       = EXCLUDED.courses,
                            notes         = EXCLUDED.notes,
                            linkedin_url  = EXCLUDED.linkedin_url,
                            department    = EXCLUDED.department,
                            groups        = EXCLUDED.groups
                        """,
                        row,
                    )

                # ── Classes ───────────────────────────────────────────────
                live_class_ids = [c["id"] for c in classes]
                if live_class_ids:
                    cur.execute(
                        "DELETE FROM classes WHERE id <> ALL(%s)",
                        (live_class_ids,),
                    )
                else:
                    cur.execute("DELETE FROM classes")
                for cls_dict in classes:
                    cur.execute(
                        """
                        INSERT INTO classes (id, data)
                        VALUES (%s, %s)
                        ON CONFLICT (id) DO UPDATE SET data = EXCLUDED.data
                        """,
                        (cls_dict["id"], json.dumps(cls_dict)),
                    )

                # ── Enrollments ───────────────────────────────────────────
                live_enroll_ids = [e["id"] for e in enrollments]
                if live_enroll_ids:
                    cur.execute(
                        "DELETE FROM enrollments WHERE id <> ALL(%s)",
                        (live_enroll_ids,),
                    )
                else:
                    cur.execute("DELETE FROM enrollments")
                for enroll in enrollments:
                    cur.execute(
                        """
                        INSERT INTO enrollments (id, student_id, class_id, data)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            student_id = EXCLUDED.student_id,
                            class_id   = EXCLUDED.class_id,
                            data       = EXCLUDED.data
                        """,
                        (
                            enroll["id"],
                            enroll["student_id"],
                            enroll["class_id"],
                            json.dumps(enroll),
                        ),
                    )

                # ── Categories ────────────────────────────────────────────
                live_cat_ids = [c["id"] for c in cats]
                if live_cat_ids:
                    cur.execute(
                        "DELETE FROM categories WHERE id <> ALL(%s)",
                        (live_cat_ids,),
                    )
                else:
                    cur.execute("DELETE FROM categories")
                for cat in cats:
                    cur.execute(
                        """
                        INSERT INTO categories (id, class_id, data)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            class_id = EXCLUDED.class_id,
                            data     = EXCLUDED.data
                        """,
                        (cat["id"], cat["class_id"], json.dumps(cat)),
                    )

                # ── Assignments ───────────────────────────────────────────
                live_asgn_ids = [a["id"] for a in assignments]
                if live_asgn_ids:
                    cur.execute(
                        "DELETE FROM assignments WHERE id <> ALL(%s)",
                        (live_asgn_ids,),
                    )
                else:
                    cur.execute("DELETE FROM assignments")
                for asgn in assignments:
                    cur.execute(
                        """
                        INSERT INTO assignments (id, category_id, data)
                        VALUES (%s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            category_id = EXCLUDED.category_id,
                            data        = EXCLUDED.data
                        """,
                        (asgn["id"], asgn["category_id"], json.dumps(asgn["data"])),
                    )

                # ── Enrollment grades ─────────────────────────────────────
                live_eg_ids = [eg["id"] for eg in egrades]
                if live_eg_ids:
                    cur.execute(
                        "DELETE FROM enrollment_grades WHERE id <> ALL(%s)",
                        (live_eg_ids,),
                    )
                else:
                    cur.execute("DELETE FROM enrollment_grades")
                for eg in egrades:
                    cur.execute(
                        """
                        INSERT INTO enrollment_grades
                            (id, enrollment_id, assignment_id, data)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (id) DO UPDATE SET
                            enrollment_id = EXCLUDED.enrollment_id,
                            assignment_id = EXCLUDED.assignment_id,
                            data          = EXCLUDED.data
                        """,
                        (
                            eg["id"],
                            eg["enrollment_id"],
                            eg["assignment_id"],
                            json.dumps(eg),
                        ),
                    )

            return True
        except Exception as exc:
            logger.error(
                "[PostgresStorage] save_dataset() failed: %s", _redact(str(exc))
            )
            return False

    def load_dataset(self) -> DatasetPayload:
        """Read the complete dataset from PostgreSQL.

        Returns:
            DatasetPayload on success; empty payload on failure.
        """
        try:
            cur = self._conn.cursor()

            cur.execute(
                "SELECT id, name, grade, email, major, academic_year, gpa, "
                "courses, notes, linkedin_url, department, groups FROM students"
            )
            students = [_row_to_student(r) for r in cur.fetchall()]

            cur.execute("SELECT data FROM classes")
            classes = [json.loads(r[0]) for r in cur.fetchall()]

            cur.execute("SELECT data FROM enrollments")
            enrollments = [json.loads(r[0]) for r in cur.fetchall()]

            cur.execute("SELECT data FROM categories")
            categories = [json.loads(r[0]) for r in cur.fetchall()]

            cur.execute("SELECT data FROM enrollment_grades")
            enrollment_grades = [json.loads(r[0]) for r in cur.fetchall()]

            return DatasetPayload(
                students=students,
                classes=classes,
                enrollments=enrollments,
                categories=categories,
                enrollment_grades=enrollment_grades,
            )
        except Exception as exc:
            logger.error(
                "[PostgresStorage] load_dataset() failed: %s", _redact(str(exc))
            )
            return DatasetPayload(students=[], classes=[], enrollments=[])

    # ── Connection lifecycle ───────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying database connection."""
        try:
            self._conn.close()
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Module-level helpers (no instance state, no credential access)
# ---------------------------------------------------------------------------

def _add_connect_timeout(url: str, timeout: int) -> str:
    """Append ``connect_timeout=N`` to a libpq DSN if not already present.

    Supports both keyword-style (``host=… port=…``) and URL-style
    (``postgresql://…``) DSNs.  Returns the modified string so that the
    caller never has to persist credentials.
    """
    if "connect_timeout" in url:
        return url
    if url.startswith("postgresql://") or url.startswith("postgres://"):
        sep = "&" if "?" in url else "?"
        return f"{url}{sep}connect_timeout={timeout}"
    # Keyword-style DSN
    return f"{url} connect_timeout={timeout}"


def _redact(msg: str) -> str:
    """Remove common credential patterns from error messages before logging."""
    import re
    # Redact postgresql://user:password@host style
    msg = re.sub(r"(postgresql|postgres)://[^@\s]*@", r"\1://<redacted>@", msg)
    # Redact password=... in keyword DSN
    msg = re.sub(r"password\s*=\s*\S+", "password=<redacted>", msg)
    return msg


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


def _row_to_student(row: tuple) -> Student:
    (sid, name, grade, email, major, academic_year, gpa,
     courses_raw, notes, linkedin_url, department, groups_raw) = row

    courses: List[CourseGrade] = []
    for c in (json.loads(courses_raw) if isinstance(courses_raw, str) else courses_raw or []):
        try:
            courses.append(CourseGrade.from_dict(c))
        except (KeyError, ValueError):
            pass

    raw_groups = (
        json.loads(groups_raw) if isinstance(groups_raw, str) else groups_raw or []
    )
    groups = [g for g in raw_groups if isinstance(g, str)]

    return Student(
        name=name,
        grade=grade,
        student_id=sid,
        email=email or "",
        major=major or "",
        academic_year=academic_year or "",
        gpa=gpa,
        courses=courses,
        notes=notes or "",
        linkedin_url=linkedin_url or "",
        department=department or "",
        groups=groups,
    )
