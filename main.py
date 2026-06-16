
"""
Student Grade Management System — Entry Point.

Wires together all layers (storage → service → UI) and
runs the main event loop.

Usage:
    python main.py
"""

import sys

from app.config import (
    MENU_ADD, MENU_REMOVE, MENU_UPDATE, MENU_VIEW_ALL,
    MENU_SEARCH, MENU_STATS, MENU_SORT, MENU_SAVE, MENU_EXIT,
)
from app.storage.json_storage import JsonStorage
from app.services.student_manager import StudentManager
from app.ui.colors import Colors
from app.ui.display import Display
from app.ui.input_helpers import InputHelper
from app.ui.handlers import MenuHandler


# ── Menu Dispatch Table ──────────────────────────────────────────────────
# Maps menu choice → handler function.  Adding a feature is one line here
# + one handler method in MenuHandler.

MENU_DISPATCH = {
    MENU_ADD:      MenuHandler.add_student,
    MENU_REMOVE:   MenuHandler.remove_student,
    MENU_UPDATE:   MenuHandler.update_grade,
    MENU_VIEW_ALL: MenuHandler.view_all,
    MENU_SEARCH:   MenuHandler.search,
    MENU_STATS:    MenuHandler.statistics,
    MENU_SORT:     MenuHandler.sort,
    MENU_SAVE:     MenuHandler.save,
}


def main() -> None:
    """Application entry point — initializes dependencies and runs the loop."""

    # 1. Enable colored output on Windows
    Colors.enable_windows_ansi()

    # 2. Wire dependencies  (Dependency Injection)
    storage = JsonStorage()                 # ← swap to SqliteStorage() etc.
    manager = StudentManager(storage)

    # 3. Load persisted data
    Display.header()
    Display.info("Loading saved data...")
    count = manager.load()
    if count > 0:
        Display.success(f"Loaded {count} student(s) from file.")
    else:
        Display.info("No existing data found. Starting fresh.")

    # 4. Main event loop
    while True:
        print()
        Display.menu()
        print()

        choice = InputHelper.get_int("👉 Enter your choice (1-9): ")

        if choice == MENU_EXIT:
            MenuHandler.exit_app(manager)
            sys.exit(0)

        handler = MENU_DISPATCH.get(choice)
        if handler:
            handler(manager)
        else:
            Display.error("Invalid choice. Please select 1-9.")

        InputHelper.pause()


if __name__ == "__main__":
    main()
