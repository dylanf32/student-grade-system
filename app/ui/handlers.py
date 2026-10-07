"""
Menu handlers — each menu option mapped to a single handler function.

Handlers bridge the UI layer and the service layer:
  1. Collect user input  (via InputHelper)
  2. Call service methods (via StudentManager / StatisticsService)
  3. Show results        (via Display)

Adding a new feature = adding one new handler + one menu entry.
"""

import os

from app.config import DATA_DIR
from app.services.student_manager import StudentManager
from app.services.statistics_service import StatisticsService
from app.ui.colors import Colors
from app.ui.display import Display
from app.ui.input_helpers import InputHelper


class MenuHandler:
    """Contains one static method per menu option."""

    # ── 1. Add Student ───────────────────────────────────────────────────

    @staticmethod
    def add_student(manager: StudentManager) -> None:
        """Prompts for name + grade and adds a new student."""
        Display.section_header("Add New Student", "➕", Colors.GREEN)

        name  = InputHelper.get_str("Enter student name: ")
        grade = InputHelper.get_grade("Enter grade (0-100): ")

        try:
            student = manager.add_student(name, grade)
            Display.success(f"Student '{student.name}' added with grade {student.grade}.")
        except ValueError as e:
            Display.error(str(e))
            return

        Display.student_table(manager.get_all_students())

    # ── 2. Remove Student ────────────────────────────────────────────────

    @staticmethod
    def remove_student(manager: StudentManager) -> None:
        """Displays students, prompts for index, removes."""
        Display.section_header("Remove Student", "➖", Colors.RED)

        if manager.is_empty():
            Display.warn("No students to remove.")
            return

        Display.student_table(manager.get_all_students())
        index = InputHelper.get_int("Enter index of student to remove: ")

        try:
            removed = manager.remove_student(index)
            Display.success(f"Removed student: {removed.name}")
        except ValueError as e:
            Display.error(str(e))
            return

        Display.student_table(manager.get_all_students())

    # ── 3. Update Grade ──────────────────────────────────────────────────

    @staticmethod
    def update_grade(manager: StudentManager) -> None:
        """Displays students, prompts for index + new grade, updates."""
        Display.section_header("Update Grade", "✏️ ", Colors.SKY)

        if manager.is_empty():
            Display.warn("No students to update.")
            return

        Display.student_table(manager.get_all_students())
        index     = InputHelper.get_int("Enter index of student to update: ")
        new_grade = InputHelper.get_grade("Enter new grade (0-100): ")

        try:
            updated = manager.update_grade(index, new_grade)
            Display.success(f"Updated {updated.name}'s grade to {updated.grade}.")
        except ValueError as e:
            Display.error(str(e))

    # ── 4. View All Students ─────────────────────────────────────────────

    @staticmethod
    def view_all(manager: StudentManager) -> None:
        """Shows the full student table."""
        Display.section_header("Student Directory", "📄", Colors.TEAL)
        Display.student_table(manager.get_all_students())

    # ── 5. Search by Name ────────────────────────────────────────────────

    @staticmethod
    def search(manager: StudentManager) -> None:
        """Prompts for a name and shows all matching students.

        Multiple students may share the same name; all matches are shown,
        each identified by their stable UUID so the user can select the
        correct one by index for further operations.
        """
        Display.section_header("Search Student", "🔍", Colors.LAVENDER)

        if manager.is_empty():
            Display.warn("No students in the system.")
            return

        name    = InputHelper.get_str("Enter name to search: ")
        matches = manager.search_all_by_name(name)

        C = Colors
        if not matches:
            Display.error(f"Student '{name}' not found.")
        else:
            print()
            print(f"  {C.GOLD}{C.BOLD}🎯 {len(matches)} match(es) found for '{name}':{C.END}")
            for index, student in matches:
                student_display_id = Display._format_id(index)
                color, status, _, _ = Display._grade_badge(student.grade)
                print(f"  {C.DIM}┌{'─' * 44}┐{C.END}")
                print(f"  {C.DIM}│{C.END}  {C.DIM}UUID:{C.END}  {C.DIM}{student.id}{C.END}")
                print(f"  {C.DIM}│{C.END}  {C.DIM}ID:{C.END}    {C.WHITE}{student_display_id}{C.END}")
                print(f"  {C.DIM}│{C.END}  {C.DIM}Index:{C.END} {C.WHITE}{C.BOLD}{index}{C.END}")
                print(f"  {C.DIM}│{C.END}  {C.DIM}Name:{C.END}  {C.WHITE}{C.BOLD}{student.name}{C.END}")
                print(f"  {C.DIM}│{C.END}  {C.DIM}Grade:{C.END} {color}{C.BOLD}{student.grade}{C.END}  {C.DIM}({status}){C.END}")
                print(f"  {C.DIM}└{'─' * 44}┘{C.END}")

    # ── 6. Statistics ────────────────────────────────────────────────────

    @staticmethod
    def statistics(manager: StudentManager) -> None:
        """Computes and displays class statistics + ranked list."""
        Display.section_header("Class Statistics", "📊", Colors.ORANGE)

        if manager.is_empty():
            Display.warn("No students to compute statistics.")
            return

        students = manager.get_all_students()
        stats    = StatisticsService.compute(students)
        ranked   = StatisticsService.get_sorted(students, ascending=False)

        Display.statistics(stats)
        Display.ranked_list(ranked)

    # ── 7. Sort by Grade ─────────────────────────────────────────────────

    @staticmethod
    def sort(manager: StudentManager) -> None:
        """Prompts for sort direction and sorts in-place."""
        Display.section_header("Sort Students", "🔃", Colors.CYAN)

        if manager.is_empty():
            Display.warn("No students to sort.")
            return

        C = Colors
        print(f"\n  {C.WHITE}{C.BOLD}  Choose sort order:{C.END}")
        print(f"    {C.LIME}{C.BOLD}1.{C.END} {C.WHITE}Ascending  (lowest → highest){C.END}")
        print(f"    {C.PINK}{C.BOLD}2.{C.END} {C.WHITE}Descending (highest → lowest){C.END}")
        print()

        while True:
            choice = InputHelper.get_int("Choose sort order (1 or 2): ")
            if choice in (1, 2):
                break
            Display.error("Invalid choice. Please enter 1 or 2.")
        ascending = choice != 2

        manager.sort_by_grade(ascending=ascending)
        order = "ascending ↑" if ascending else "descending ↓"
        Display.success(f"Students sorted by grade ({order}).")
        Display.student_table(manager.get_all_students())

    # ── 8. Save ──────────────────────────────────────────────────────────

    @staticmethod
    def save(manager: StudentManager) -> None:
        """Persists current data to disk."""
        Display.section_header("Save Data", "💾", Colors.GREEN)
        if manager.save():
            Display.success("Data saved successfully to disk.")
        else:
            Display.error("Failed to save data.")

    # ── 9. Exit ──────────────────────────────────────────────────────────

    @staticmethod
    def exit_app(manager: StudentManager) -> None:
        """Auto-saves and prints goodbye message."""
        C = Colors
        Display.section_header("Exiting...", "🚪", Colors.INDIGO)
        print(f"  {C.DIM}  Saving data before exit...{C.END}")
        manager.save()
        print()
        print(f"  {C.INDIGO}{C.BOLD}╔{'═' * 50}╗{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}{C.BG_DEEP}{C.WHITE}{C.BOLD}{'👋  Goodbye! Thank you for using the system.':^50}{C.END}{C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}╚{'═' * 50}╝{C.END}")
        print()

    # ── 10. Analytics Dashboard ──────────────────────────────────────────

    @staticmethod
    def analytics_dashboard(manager: StudentManager) -> None:
        """Computes and displays the full academic analytics dashboard."""
        Display.section_header("Academic Analytics Dashboard", "📈", Colors.TEAL)

        if manager.is_empty():
            Display.warn("No students to analyse.")
            return

        students = manager.get_all_students()
        dash = StatisticsService.compute_analytics(students)
        Display.analytics_dashboard(dash)

    # ── 11. At-Risk Detection ────────────────────────────────────────────

    @staticmethod
    def at_risk(manager: StudentManager) -> None:
        """Identifies and displays at-risk students."""
        Display.section_header("At-Risk Student Detection", "⚠️ ", Colors.RED)

        if manager.is_empty():
            Display.warn("No students in the system.")
            return

        students = manager.get_all_students()
        at_risk_list = StatisticsService.detect_at_risk(students)
        Display.at_risk_report(at_risk_list)

    # ── 12. Export CSV ───────────────────────────────────────────────────

    @staticmethod
    def export_csv(manager: StudentManager) -> None:
        """Exports all students to a CSV file in the data directory."""
        Display.section_header("Export Students to CSV", "📤", Colors.GREEN)

        if manager.is_empty():
            Display.warn("No students to export.")
            return

        C = Colors
        default_path = os.path.join(DATA_DIR, "students_export.csv")
        print(f"  {C.DIM}Default path: {default_path}{C.END}")
        raw = input(
            f"  {C.INDIGO}{C.BOLD}▸{C.END} {C.WHITE}Export path (Enter for default): {C.END}"
        ).strip()
        filepath = raw if raw else default_path

        try:
            count = manager.export_csv(filepath)
            Display.csv_result("Exported", count, [])
            Display.info(f"File saved to: {filepath}")
        except OSError as exc:
            Display.error(f"Export failed: {exc}")

    # ── 13. Import CSV ───────────────────────────────────────────────────

    @staticmethod
    def import_csv(manager: StudentManager) -> None:
        """Imports students from a CSV file, appending to the current list."""
        Display.section_header("Import Students from CSV", "📥", Colors.SKY)

        C = Colors
        filepath = input(
            f"  {C.INDIGO}{C.BOLD}▸{C.END} {C.WHITE}CSV file path to import: {C.END}"
        ).strip()
        if not filepath:
            Display.error("No path entered.")
            return
        if not os.path.isfile(filepath):
            Display.error(f"File not found: {filepath}")
            return

        try:
            imported, errors = manager.import_csv(filepath)
            Display.csv_result("Imported", imported, errors)
            if imported:
                Display.student_table(manager.get_all_students())
        except OSError as exc:
            Display.error(f"Import failed: {exc}")
