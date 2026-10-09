"""
Migration script: JSON → SQLite

Reads all students from data/students.json and writes them into
data/students.db using SqliteStorage.  The original JSON file is
left untouched.

Usage:
    python migrate_to_sqlite.py

Safe to re-run: the SQLite table is replaced atomically on each run,
so duplicate runs do not create duplicate rows.
"""

import sys
from app.storage.json_storage import JsonStorage
from app.storage.sqlite_storage import SqliteStorage
from app.config import DEFAULT_DATA_FILE, DEFAULT_DB_FILE


def main() -> int:
    json_store = JsonStorage(DEFAULT_DATA_FILE)
    students = json_store.load()
    print(f"Loaded {len(students)} student(s) from {DEFAULT_DATA_FILE}")

    db_store = SqliteStorage(DEFAULT_DB_FILE)
    if db_store.save(students):
        print(f"Migrated {len(students)} student(s) -> {DEFAULT_DB_FILE}")
        return 0
    else:
        print("Migration failed — SQLite save returned False.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
