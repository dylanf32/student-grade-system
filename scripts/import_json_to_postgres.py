"""
JSON → PostgreSQL import command.

Reads the v1/v2/v3 JSON data file, writes a timestamped backup of that file
beside it, then imports all entities into PostgreSQL inside a single
transaction.  On any failure the transaction is rolled back and the database
is left unchanged.

Usage
-----
Set DATABASE_URL in the environment, then run::

    python scripts/import_json_to_postgres.py [path/to/students.json]

If no path is given the default data file from app.config is used.

UUID collision handling
-----------------------
Any entity whose UUID already exists in the database is *skipped* (not
overwritten).  The counts reported at the end include a ``skipped`` column
so the operator can tell whether a partial re-import occurred.

The script never performs a destructive replacement of the whole database.
Rows for UUIDs that are absent from the JSON file are left in PostgreSQL
untouched.

Safety
------
- No automatic import on startup or connect.
- Credentials are read from DATABASE_URL only; never printed or logged.
- The JSON backup is written before any database work starts.
- The entire import is one atomic transaction; any error rolls back completely.
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sys
import time
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Make sure the project root is on sys.path when run directly
# ---------------------------------------------------------------------------
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from app.config import DEFAULT_DATA_FILE  # noqa: E402
from app.storage.json_storage import JsonStorage  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# psycopg2 import — optional at module level so tests can mock it
# ---------------------------------------------------------------------------
try:
    import psycopg2
    import psycopg2.extras
    _HAS_PSYCOPG2 = True
except ImportError:
    psycopg2 = None  # type: ignore[assignment]
    _HAS_PSYCOPG2 = False


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _redact(msg: str) -> str:
    """Remove credential patterns before logging."""
    msg = re.sub(r"(postgresql|postgres)://[^@\s]*@", r"\1://<redacted>@", msg)
    msg = re.sub(r"password\s*=\s*\S+", "password=<redacted>", msg)
    return msg


def _backup_json(source_path: str) -> str:
    """Write a timestamped copy of *source_path* beside it.

    Returns the backup file path.
    Raises IOError / OSError if the copy cannot be made.
    """
    ts = time.strftime("%Y%m%d_%H%M%S")
    backup_path = source_path + f".backup_{ts}"
    shutil.copy2(source_path, backup_path)
    logger.info("Backup written: %s", backup_path)
    return backup_path


def _load_json_payload(json_path: str) -> Dict[str, List[Any]]:
    """Load the JSON file via JsonStorage (handles v1/v2/v3 transparently).

    Returns a dict with keys:
        students, classes, enrollments, categories, enrollment_grades
    """
    storage = JsonStorage(json_path)
    payload = storage.load_dataset()
    return {
        "students":          [s.to_dict() for s in payload.students],
        "classes":           payload.classes,
        "enrollments":       payload.enrollments,
        "categories":        payload.categories,
        "enrollment_grades": payload.enrollment_grades,
    }


# ---------------------------------------------------------------------------
# UUID collision handling — INSERT … ON CONFLICT DO NOTHING
# ---------------------------------------------------------------------------

def _import_students(cur, students: List[dict]) -> Tuple[int, int]:
    """Insert students; skip existing UUIDs.  Returns (inserted, skipped)."""
    inserted = skipped = 0
    for s in students:
        cur.execute(
            """
            INSERT INTO students
                (id, name, grade, email, major, academic_year, gpa,
                 courses, notes, linkedin_url, department, groups)
            VALUES
                (%(id)s, %(name)s, %(grade)s, %(email)s, %(major)s,
                 %(academic_year)s, %(gpa)s, %(courses)s::jsonb, %(notes)s,
                 %(linkedin_url)s, %(department)s, %(groups)s::jsonb)
            ON CONFLICT (id) DO NOTHING
            """,
            {
                "id":            s["id"],
                "name":          s["name"],
                "grade":         s["grade"],
                "email":         s.get("email", ""),
                "major":         s.get("major", ""),
                "academic_year": s.get("academic_year", ""),
                "gpa":           s.get("gpa"),
                "courses":       json.dumps(s.get("courses", [])),
                "notes":         s.get("notes", ""),
                "linkedin_url":  s.get("linkedin_url", ""),
                "department":    s.get("department", ""),
                "groups":        json.dumps(s.get("groups", [])),
            },
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def _import_simple(cur, table: str, rows: List[dict]) -> Tuple[int, int]:
    """Insert rows into a table with (id, data) columns; skip collisions."""
    inserted = skipped = 0
    for row in rows:
        cur.execute(
            f"""
            INSERT INTO {table} (id, data)
            VALUES (%s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (row["id"], json.dumps(row)),
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def _import_enrollments(cur, enrollments: List[dict]) -> Tuple[int, int]:
    """Insert enrollments with FK columns; skip collisions."""
    inserted = skipped = 0
    for e in enrollments:
        cur.execute(
            """
            INSERT INTO enrollments (id, student_id, class_id, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (e["id"], e["student_id"], e["class_id"], json.dumps(e)),
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


def _import_categories_and_assignments(
    cur, categories: List[dict]
) -> Tuple[Tuple[int, int], Tuple[int, int]]:
    """Insert categories (with FK) and their nested assignments.

    Returns ((cat_inserted, cat_skipped), (asgn_inserted, asgn_skipped)).
    """
    cat_ins = cat_sk = asgn_ins = asgn_sk = 0
    for cat in categories:
        cur.execute(
            """
            INSERT INTO categories (id, class_id, data)
            VALUES (%s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (cat["id"], cat["class_id"], json.dumps(cat)),
        )
        if cur.rowcount == 1:
            cat_ins += 1
        else:
            cat_sk += 1
        for asgn in cat.get("assignments", []):
            cur.execute(
                """
                INSERT INTO assignments (id, category_id, data)
                VALUES (%s, %s, %s)
                ON CONFLICT (id) DO NOTHING
                """,
                (asgn["id"], cat["id"], json.dumps(asgn)),
            )
            if cur.rowcount == 1:
                asgn_ins += 1
            else:
                asgn_sk += 1
    return (cat_ins, cat_sk), (asgn_ins, asgn_sk)


def _import_enrollment_grades(cur, egrades: List[dict]) -> Tuple[int, int]:
    """Insert enrollment_grades with FK columns; skip collisions."""
    inserted = skipped = 0
    for eg in egrades:
        cur.execute(
            """
            INSERT INTO enrollment_grades (id, enrollment_id, assignment_id, data)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (id) DO NOTHING
            """,
            (eg["id"], eg["enrollment_id"], eg["assignment_id"], json.dumps(eg)),
        )
        if cur.rowcount == 1:
            inserted += 1
        else:
            skipped += 1
    return inserted, skipped


# ---------------------------------------------------------------------------
# Main import function (importable for tests)
# ---------------------------------------------------------------------------

def import_json_to_postgres(json_path: str, database_url: str) -> bool:
    """Import *json_path* into PostgreSQL at *database_url*.

    Steps:
    1. Back up the JSON file (abort if backup fails).
    2. Load the JSON via JsonStorage (v1/v2/v3 transparent).
    3. Open one connection, run all INSERTs inside a single transaction.
    4. On any failure, roll back and return False.
    5. On success, log verified entity counts and return True.

    Args:
        json_path:    Path to the JSON data file.
        database_url: libpq DSN from DATABASE_URL env var.

    Returns:
        True on success, False on any failure.
    """
    # ── 0. Check driver ──────────────────────────────────────────────────────
    if not _HAS_PSYCOPG2:
        logger.error(
            "psycopg2 is required. Install it with: pip install psycopg2-binary"
        )
        return False

    # ── 1. Backup ────────────────────────────────────────────────────────────
    try:
        _backup_json(json_path)
    except OSError as exc:
        logger.error("Backup failed: %s — aborting import.", exc)
        return False

    # ── 2. Load JSON ─────────────────────────────────────────────────────────
    try:
        data = _load_json_payload(json_path)
    except Exception as exc:
        logger.error("Failed to read JSON: %s", exc)
        return False

    # ── 3. Connect and import ─────────────────────────────────────────────────
    conn = None
    try:
        conn = psycopg2.connect(database_url)
        conn.autocommit = False
        cur = conn.cursor()

        s_ins, s_sk = _import_students(cur, data["students"])
        c_ins, c_sk = _import_simple(cur, "classes", data["classes"])
        e_ins, e_sk = _import_enrollments(cur, data["enrollments"])
        (cat_ins, cat_sk), (asgn_ins, asgn_sk) = _import_categories_and_assignments(
            cur, data["categories"]
        )
        eg_ins, eg_sk = _import_enrollment_grades(cur, data["enrollment_grades"])

        conn.commit()

        # ── 4. Verified entity counts ─────────────────────────────────────────
        logger.info(
            "Import complete:\n"
            "  students          inserted=%d  skipped=%d\n"
            "  classes           inserted=%d  skipped=%d\n"
            "  enrollments       inserted=%d  skipped=%d\n"
            "  categories        inserted=%d  skipped=%d\n"
            "  assignments       inserted=%d  skipped=%d\n"
            "  enrollment_grades inserted=%d  skipped=%d",
            s_ins, s_sk, c_ins, c_sk, e_ins, e_sk,
            cat_ins, cat_sk, asgn_ins, asgn_sk, eg_ins, eg_sk,
        )
        return True

    except Exception as exc:
        logger.error("Import failed, rolling back: %s", _redact(str(exc)))
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass
        return False
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> None:
    if not _HAS_PSYCOPG2:
        logger.error(
            "psycopg2 is required. Install it with: pip install psycopg2-binary"
        )
        sys.exit(1)
    json_path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_DATA_FILE
    database_url = os.environ.get("DATABASE_URL", "")
    if not database_url:
        logger.error(
            "DATABASE_URL environment variable is not set. "
            "Set it to a PostgreSQL connection URL and retry."
        )
        sys.exit(1)
    if not os.path.exists(json_path):
        logger.error("JSON file not found: %s", json_path)
        sys.exit(1)

    ok = import_json_to_postgres(json_path, database_url)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
