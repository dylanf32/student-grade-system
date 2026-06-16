"""
Display helpers — functions that render formatted output to the console.

All print-to-screen logic lives here.  The service layer never prints;
it only returns data, and this module formats and displays it.
"""

import os
from typing import List

from app.config import GRADE_EXCELLENT, GRADE_GOOD, GRADE_AVERAGE, GRADE_BELOW_AVG
from app.models.student import Student
from app.services.statistics_service import GradeStats
from app.ui.colors import Colors


class Display:
    """Static helper methods for premium console rendering."""

    # ── Terminal Width ────────────────────────────────────────────────────
    WIDTH = 62

    # ── Screen Clear ─────────────────────────────────────────────────────

    @staticmethod
    def clear_screen() -> None:
        """Clears the terminal screen."""
        os.system('cls' if os.name == 'nt' else 'clear')

    # ── Banner ───────────────────────────────────────────────────────────

    @staticmethod
    def header() -> None:
        """Prints a premium application banner."""
        W = Display.WIDTH
        C = Colors
        print()
        print(f"  {C.INDIGO}{C.BOLD}╔{'═' * W}╗{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}{C.BG_DEEP}{C.LAVENDER}{C.BOLD}{'':^{W}}{C.END}{C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}{C.BG_DEEP}{C.WHITE}{C.BOLD}{'📚  STUDENT GRADE MANAGEMENT SYSTEM  📚':^{W}}{C.END}{C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}{C.BG_DEEP}{C.SKY}{'Academic Performance Control Center':^{W}}{C.END}{C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}{C.BG_DEEP}{C.LAVENDER}{C.BOLD}{'':^{W}}{C.END}{C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}╚{'═' * W}╝{C.END}")
        print()

    # ── Main Menu ────────────────────────────────────────────────────────

    @staticmethod
    def menu() -> None:
        """Renders a premium styled numbered main menu."""
        W = Display.WIDTH
        C = Colors

        print(f"  {C.INDIGO}{C.BOLD}╔{'═' * W}╗{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}{C.BG_DEEP}{C.GOLD}{C.BOLD}{'📋  MAIN MENU':^{W}}{C.END}{C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}╠{'═' * W}╣{C.END}")

        menu_items = [
            ("1", "➕", "Add Student",             C.LIME),
            ("2", "➖", "Remove Student",          C.PINK),
            ("3", "✏️ ", "Update Grade",             C.SKY),
            ("4", "📄", "View All Students",       C.TEAL),
            ("5", "🔍", "Search Student by Name",  C.LAVENDER),
            ("6", "📊", "View Statistics",         C.ORANGE),
            ("7", "🔃", "Sort by Grade",           C.CYAN),
            ("8", "💾", "Save Data",               C.GREEN),
            ("9", "🚪", "Exit",                    C.RED),
        ]

        for num, icon, label, color in menu_items:
            padded = f"   {C.WHITE}{C.BOLD}{num}.{C.END} {icon}  {color}{label}{C.END}"
            # We need to calculate visible length excluding ANSI codes
            print(f"  {C.INDIGO}{C.BOLD}║{C.END}  {padded}")

        print(f"  {C.INDIGO}{C.BOLD}╚{'═' * W}╝{C.END}")

    # ── Section Headers ──────────────────────────────────────────────────

    @staticmethod
    def section_header(title: str, icon: str = "▸", color: str = Colors.INDIGO) -> None:
        """Prints a styled section header with a decorative border.

        Args:
            title: The section title text.
            icon:  An emoji or character prefix.
            color: ANSI color for the border.
        """
        W = Display.WIDTH
        C = Colors
        print()
        print(f"  {color}{C.BOLD}┌{'─' * W}┐{C.END}")
        print(f"  {color}{C.BOLD}│{C.END}  {C.WHITE}{C.BOLD}{icon}  {title}{C.END}")
        print(f"  {color}{C.BOLD}└{'─' * W}┘{C.END}")

    # ── Student Table ────────────────────────────────────────────────────

    # Column widths shared by the header, rows, and borders below.
    _COL_INDEX: int = 5
    _COL_ID: int = 9
    _COL_NAME: int = 20
    _COL_GRADE: int = 7
    _COL_STATUS: int = 15

    @staticmethod
    def student_table(students: List[Student]) -> None:
        """Renders all students in a color-coded, premium boxed table.

        Each row also shows a friendly Student ID (e.g. ``STU-001``)
        positioned just before the name, in addition to the raw list
        index used by the other menu actions.

        Args:
            students: The list to display.
        """
        if not students:
            Display._empty_state("No students in the system yet.")
            return

        C = Colors
        ci, cid, cn, cg, cs = (
            Display._COL_INDEX, Display._COL_ID,
            Display._COL_NAME, Display._COL_GRADE, Display._COL_STATUS,
        )

        total_w = ci + cid + cn + cg + cs + 14  # padding between columns

        # ── Top border
        print(f"\n  {C.INDIGO}{C.BOLD}╔{'═' * (ci + 2)}╦{'═' * (cid + 2)}╦{'═' * (cn + 2)}╦{'═' * (cg + 2)}╦{'═' * (cs + 2)}╗{C.END}")

        # ── Header row
        print(
            f"  {C.INDIGO}{C.BOLD}║{C.END} {C.GOLD}{C.BOLD}{'#':<{ci}}{C.END} "
            f"{C.INDIGO}{C.BOLD}║{C.END} {C.GOLD}{C.BOLD}{'ID':<{cid}}{C.END} "
            f"{C.INDIGO}{C.BOLD}║{C.END} {C.GOLD}{C.BOLD}{'Name':<{cn}}{C.END} "
            f"{C.INDIGO}{C.BOLD}║{C.END} {C.GOLD}{C.BOLD}{'Grade':<{cg}}{C.END} "
            f"{C.INDIGO}{C.BOLD}║{C.END} {C.GOLD}{C.BOLD}{'Status':<{cs}}{C.END} "
            f"{C.INDIGO}{C.BOLD}║{C.END}"
        )

        # ── Separator
        print(f"  {C.INDIGO}{C.BOLD}╠{'═' * (ci + 2)}╬{'═' * (cid + 2)}╬{'═' * (cn + 2)}╬{'═' * (cg + 2)}╬{'═' * (cs + 2)}╣{C.END}")

        # ── Data rows
        for i, s in enumerate(students):
            grade = s.grade
            color, status_text, badge_fg, badge_bg = Display._grade_badge(grade)
            student_id = Display._format_id(i)

            status_badge = Colors.badge(f"{status_text:^11}", badge_fg, badge_bg)

            print(
                f"  {C.INDIGO}{C.BOLD}║{C.END} {C.WHITE}{C.BOLD}{i:<{ci}}{C.END} "
                f"{C.INDIGO}{C.BOLD}║{C.END} {C.DIM}{student_id:<{cid}}{C.END} "
                f"{C.INDIGO}{C.BOLD}║{C.END} {C.WHITE}{s.name:<{cn}}{C.END} "
                f"{C.INDIGO}{C.BOLD}║{C.END} {color}{C.BOLD}{grade:<{cg}}{C.END} "
                f"{C.INDIGO}{C.BOLD}║{C.END} {status_badge} "
                f"{C.INDIGO}{C.BOLD}║{C.END}"
            )

        # ── Bottom border
        print(f"  {C.INDIGO}{C.BOLD}╚{'═' * (ci + 2)}╩{'═' * (cid + 2)}╩{'═' * (cn + 2)}╩{'═' * (cg + 2)}╩{'═' * (cs + 2)}╝{C.END}")

        # ── Summary
        print(f"\n  {C.DIM}{'─' * 40}{C.END}")
        print(f"  {C.SKY}{C.BOLD}  Total Students: {len(students)}{C.END}")

    @staticmethod
    def _format_id(index: int) -> str:
        """Builds a friendly, zero-padded Student ID from a list index.

        This is a display-only label (e.g. ``STU-001``) used to make the
        table easier to read at a glance. It mirrors the 0-based list
        index used elsewhere for selecting students.

        Args:
            index: 0-based position in the student list.

        Returns:
            An alphanumeric ID such as ``"STU-001"``.
        """
        return f"STU-{index + 1:03d}"

    # ── Statistics Box ───────────────────────────────────────────────────

    @staticmethod
    def statistics(stats: GradeStats) -> None:
        """Renders statistics in a premium bordered box with visual bars.

        Args:
            stats: A computed GradeStats dataclass.
        """
        C = Colors
        W = Display.WIDTH

        # Passing rate visual bar
        if stats.total_students > 0:
            pass_rate = round(stats.passing_count / stats.total_students * 100, 1)
            bar_len = 30
            filled = int(pass_rate / 100 * bar_len)
            bar = f"{C.GREEN}{'█' * filled}{C.DIM}{'░' * (bar_len - filled)}{C.END}"
        else:
            pass_rate = 0.0
            bar = f"{C.DIM}{'░' * 30}{C.END}"

        print(f"\n  {C.INDIGO}{C.BOLD}╔{'═' * W}╗{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}{C.BG_DEEP}{C.GOLD}{C.BOLD}{'📊  CLASS STATISTICS':^{W}}{C.END}{C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}╠{'═' * W}╣{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}                                                              {C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}   {C.SKY}👥 Total Students  :{C.END}  {C.WHITE}{C.BOLD}{stats.total_students}{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}   {C.TEAL}📈 Average Grade   :{C.END}  {C.WHITE}{C.BOLD}{stats.average}{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}   {C.LIME}🏆 Highest Grade   :{C.END}  {C.GREEN}{C.BOLD}{stats.highest}{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}   {C.PINK}📉 Lowest Grade    :{C.END}  {C.RED}{C.BOLD}{stats.lowest}{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}   {C.GREEN}✅ Passing (≥60)   :{C.END}  {C.GREEN}{C.BOLD}{stats.passing_count}{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}   {C.RED}❌ Failing (<60)   :{C.END}  {C.RED}{C.BOLD}{stats.failing_count}{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}   {C.GOLD}📊 Passing Rate:{C.END}  {bar}  {C.WHITE}{C.BOLD}{pass_rate}%{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}║{C.END}")
        print(f"  {C.INDIGO}{C.BOLD}╚{'═' * W}╝{C.END}")

    # ── Ranked List ──────────────────────────────────────────────────────

    @staticmethod
    def ranked_list(students: List[Student]) -> None:
        """Shows students ranked by grade (highest first) with medals.

        Args:
            students: Already-sorted list of students.
        """
        C = Colors

        print(f"\n  {C.GOLD}{C.BOLD}  🏅 Students Ranked by Grade (Highest → Lowest){C.END}")
        print(f"  {C.DIM}  {'─' * 50}{C.END}")

        medals = ["🥇", "🥈", "🥉"]
        for rank, s in enumerate(students):
            color, _, _, _ = Display._grade_badge(s.grade)
            medal = medals[rank] if rank < 3 else f"  {rank + 1}."
            name_padded = f"{s.name:<25}"
            print(f"    {C.BOLD}{medal}{C.END}  {C.WHITE}{name_padded}{C.END}{color}{C.BOLD}{s.grade}{C.END}")

        print(f"  {C.DIM}  {'─' * 50}{C.END}")

    # ── Empty State ──────────────────────────────────────────────────────

    @staticmethod
    def _empty_state(msg: str) -> None:
        """Displays a styled empty-state message.

        Args:
            msg: The message to display.
        """
        C = Colors
        print(f"\n  {C.DIM}┌{'─' * 44}┐{C.END}")
        print(f"  {C.DIM}│{C.END}  {C.YELLOW}📭  {msg:<38}{C.END}  {C.DIM}│{C.END}")
        print(f"  {C.DIM}└{'─' * 44}┘{C.END}")

    # ── Feedback Messages ────────────────────────────────────────────────

    @staticmethod
    def success(msg: str) -> None:
        """Prints a green success message with a badge."""
        C = Colors
        print(f"  {C.BG_GREEN}{C.WHITE}{C.BOLD} ✅ SUCCESS {C.END} {C.GREEN}{msg}{C.END}")

    @staticmethod
    def error(msg: str) -> None:
        """Prints a red error message with a badge."""
        C = Colors
        print(f"  {C.BG_RED}{C.WHITE}{C.BOLD} ❌ ERROR {C.END} {C.RED}{msg}{C.END}")

    @staticmethod
    def info(msg: str) -> None:
        """Prints a cyan info message with a badge."""
        C = Colors
        print(f"  {C.BG_CYAN}{C.WHITE}{C.BOLD} ℹ️  INFO {C.END} {C.CYAN}{msg}{C.END}")

    @staticmethod
    def warn(msg: str) -> None:
        """Prints a yellow warning message with a badge."""
        C = Colors
        print(f"  {C.BG_YELLOW}{C.WHITE}{C.BOLD} ⚠️  WARNING {C.END} {C.YELLOW}{msg}{C.END}")

    # ── Internal ─────────────────────────────────────────────────────────

    @staticmethod
    def _grade_badge(grade: int) -> tuple:
        """Returns (color_code, status_label, badge_fg, badge_bg) for a grade.

        Args:
            grade: The numeric grade.

        Returns:
            Tuple of (ANSI color, status text, badge foreground, badge background).
        """
        C = Colors
        if grade >= GRADE_EXCELLENT:
            return C.GREEN,  "🌟 Excellent", C.WHITE, C.BG_GREEN
        elif grade >= GRADE_GOOD:
            return C.CYAN,   "👍 Good",      C.WHITE, C.BG_CYAN
        elif grade >= GRADE_AVERAGE:
            return C.BLUE,   "📘 Average",   C.WHITE, C.BG_BLUE
        elif grade >= GRADE_BELOW_AVG:
            return C.YELLOW, "⚠️  Below Avg", C.WHITE, C.BG_YELLOW
        else:
            return C.RED,    "❌ Failing",   C.WHITE, C.BG_RED

    # Keep the old method name for backward compat
    @staticmethod
    def _grade_status(grade: int) -> tuple:
        """Returns (color_code, status_label) for a grade.

        Args:
            grade: The numeric grade.

        Returns:
            Tuple of (ANSI color string, emoji status string).
        """
        color, label, _, _ = Display._grade_badge(grade)
        return color, label
