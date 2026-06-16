"""
Menu handlers — each menu option mapped to a single handler function.

Handlers bridge the UI layer and the service layer:
  1. Collect user input  (via InputHelper)
  2. Call service methods (via StudentManager / StatisticsService)
  3. Show results        (via Display)

Adding a new feature = adding one new handler + one menu entry.
"""

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
        grade = InputHelper.get_int("Enter grade (0-100): ")

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
        new_grade = InputHelper.get_int("Enter new grade (0-100): ")

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
        """Prompts for a name and shows the matching student."""
        Display.section_header("Search Student", "🔍", Colors.LAVENDER)

        if manager.is_empty():
            Display.warn("No students in the system.")
            return

        name  = InputHelper.get_str("Enter name to search: ")
        index = manager.search_by_name(name)

        C = Colors
        if index == -1:
            Display.error(f"Student '{name}' not found.")
        else:
            student = manager.get_student(index)
            student_id = Display._format_id(index)
            print()
            print(f"  {C.DIM}┌{'─' * 44}┐{C.END}")
            print(f"  {C.DIM}│{C.END}  {C.GOLD}{C.BOLD}🎯 Match Found{C.END}")
            print(f"  {C.DIM}│{C.END}  {C.DIM}ID:{C.END}    {C.WHITE}{student_id}{C.END}")
            print(f"  {C.DIM}│{C.END}  {C.DIM}Index:{C.END} {C.WHITE}{C.BOLD}{index}{C.END}")
            print(f"  {C.DIM}│{C.END}  {C.DIM}Name:{C.END}  {C.WHITE}{C.BOLD}{student.name}{C.END}")
            color, status, _, _ = Display._grade_badge(student.grade)
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

        choice    = InputHelper.get_int("Choose sort order (1 or 2): ")
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
