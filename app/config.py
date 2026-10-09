"""
Configuration constants for the Student Grade Management System.

All application-wide settings are centralized here so that
changing a limit or path only requires editing one file.
"""

import os

# ── Grade Boundaries ─────────────────────────────────────────────────────
MIN_GRADE: int = 0
MAX_GRADE: int = 100

# ── File Paths ───────────────────────────────────────────────────────────
BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR: str = os.path.join(BASE_DIR, "data")
DEFAULT_DATA_FILE: str = os.path.join(DATA_DIR, "students.json")
DEFAULT_DB_FILE: str = os.path.join(DATA_DIR, "students.db")

# ── Passing Threshold ────────────────────────────────────────────────────
# Single authoritative value used by statistics, validation, and the frontend.
# A student with grade >= PASSING_THRESHOLD is counted as passing.
PASSING_THRESHOLD: int = 60

# ── Grade Band Boundaries (for display labels) ────────────────────────────
GRADE_EXCELLENT: int = 90
GRADE_GOOD: int = 80
GRADE_AVERAGE: int = 70
GRADE_BELOW_AVG: int = 60   # == PASSING_THRESHOLD; label: "Passing (D)"

# ── Menu Options ─────────────────────────────────────────────────────────
MENU_ADD = 1
MENU_REMOVE = 2
MENU_UPDATE = 3
MENU_VIEW_ALL = 4
MENU_SEARCH = 5
MENU_STATS = 6
MENU_SORT = 7
MENU_SAVE = 8
MENU_EXIT = 9
MENU_ANALYTICS = 10
MENU_AT_RISK = 11
MENU_EXPORT_CSV = 12
MENU_IMPORT_CSV = 13
