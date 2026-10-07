"""
StatisticsService — computes aggregate statistics on student grades.

Separated from StudentManager so that stats logic can grow
independently (e.g., median, standard deviation, grade distribution)
without bloating the CRUD service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from app.models.student import Student


@dataclass(frozen=True)
class GradeStats:
    """Immutable container for computed grade statistics.

    Attributes:
        total_students: Number of students.
        average:        Mean grade (rounded to 2 decimals).
        highest:        Maximum grade (float to support decimal grades).
        lowest:         Minimum grade (float to support decimal grades).
        passing_count:  Students with grade >= 60.
        failing_count:  Students with grade < 60.
    """

    total_students: int
    average: float
    highest: Optional[float]
    lowest: Optional[float]
    passing_count: int
    failing_count: int


@dataclass(frozen=True)
class AnalyticsDashboard:
    """Rich analytics snapshot for the academic dashboard.

    Attributes:
        total_students:     Headcount.
        average:            Mean grade.
        median:             Median grade.
        std_dev:            Population standard deviation.
        highest:            Max grade.
        lowest:             Min grade.
        passing_count:      Students with grade >= 60.
        failing_count:      Students with grade < 60.
        distribution:       Mapping band_label → count, e.g. {"A (90-100)": 5}.
        by_major:           Mapping major → average_grade for known majors.
        gpa_average:        Mean GPA across students that have one (or None).
        at_risk_count:      Number of at-risk students.
    """

    total_students: int
    average: float
    median: float
    std_dev: float
    highest: Optional[float]
    lowest: Optional[float]
    passing_count: int
    failing_count: int
    distribution: Dict[str, int]
    by_major: Dict[str, float]
    gpa_average: Optional[float]
    at_risk_count: int


@dataclass(frozen=True)
class AtRiskStudent:
    """One at-risk student and the reasons they were flagged.

    Attributes:
        student:  The Student object.
        reasons:  Non-empty list of human-readable risk reasons.
    """

    student: Student
    reasons: List[str]


class StatisticsService:
    """Computes read-only statistics over a list of Students.

    This service is stateless — it receives the data it needs
    as method arguments rather than holding its own copy.
    """

    PASS_THRESHOLD: int = 60

    # ── Core Statistics ──────────────────────────────────────────────────

    @staticmethod
    def compute(students: List[Student]) -> GradeStats:
        """Computes all grade statistics in a single pass.

        Args:
            students: The list of Student objects.

        Returns:
            A GradeStats dataclass with all computed values.
        """
        if not students:
            return GradeStats(
                total_students=0,
                average=0.0,
                highest=None,
                lowest=None,
                passing_count=0,
                failing_count=0,
            )

        grades = [s.grade for s in students]
        passing = sum(1 for g in grades if g >= StatisticsService.PASS_THRESHOLD)

        return GradeStats(
            total_students=len(grades),
            average=round(sum(grades) / len(grades), 2),
            highest=max(grades),
            lowest=min(grades),
            passing_count=passing,
            failing_count=len(grades) - passing,
        )

    # ── Individual Accessors (convenience) ───────────────────────────────

    @staticmethod
    def get_average(students: List[Student]) -> float:
        """Returns the mean grade, or 0.0 if empty."""
        if not students:
            return 0.0
        return round(sum(s.grade for s in students) / len(students), 2)

    @staticmethod
    def get_highest(students: List[Student]) -> Optional[float]:
        """Returns the highest grade, or None if the list is empty."""
        if not students:
            return None
        return max(s.grade for s in students)

    @staticmethod
    def get_lowest(students: List[Student]) -> Optional[float]:
        """Returns the lowest grade, or None if the list is empty."""
        if not students:
            return None
        return min(s.grade for s in students)

    @staticmethod
    def get_sorted(
        students: List[Student], ascending: bool = True
    ) -> List[Student]:
        """Returns a NEW sorted list (does not mutate the original).

        Args:
            students:  Source list.
            ascending: Sort direction.

        Returns:
            A sorted copy.
        """
        return sorted(
            students,
            key=lambda s: s.grade,
            reverse=not ascending,
        )

    # ── Analytics Dashboard ──────────────────────────────────────────────

    @staticmethod
    def compute_analytics(students: List[Student]) -> AnalyticsDashboard:
        """Computes a rich analytics snapshot.

        Args:
            students: Full student list.

        Returns:
            An AnalyticsDashboard dataclass.
        """
        if not students:
            return AnalyticsDashboard(
                total_students=0, average=0.0, median=0.0, std_dev=0.0,
                highest=None, lowest=None, passing_count=0, failing_count=0,
                distribution={b: 0 for b in StatisticsService._BANDS},
                by_major={}, gpa_average=None, at_risk_count=0,
            )

        grades = [s.grade for s in students]
        n = len(grades)
        avg = round(sum(grades) / n, 2)

        # Median
        sorted_g = sorted(grades)
        mid = n // 2
        median = round(
            (sorted_g[mid - 1] + sorted_g[mid]) / 2 if n % 2 == 0 else sorted_g[mid], 2
        )

        # Population std dev
        variance = sum((g - avg) ** 2 for g in grades) / n
        std_dev = round(variance ** 0.5, 2)

        passing = sum(1 for g in grades if g >= StatisticsService.PASS_THRESHOLD)

        # Grade distribution
        dist: Dict[str, int] = {b: 0 for b in StatisticsService._BANDS}
        for g in grades:
            dist[StatisticsService._grade_band(g)] += 1

        # Average by major (skip blank)
        major_groups: Dict[str, List[float]] = {}
        for s in students:
            if s.major:
                major_groups.setdefault(s.major, []).append(s.grade)
        by_major = {m: round(sum(gs) / len(gs), 2) for m, gs in major_groups.items()}

        # GPA average
        gpas = [s.gpa for s in students if s.gpa is not None]
        gpa_avg: Optional[float] = round(sum(gpas) / len(gpas), 2) if gpas else None

        at_risk = StatisticsService.detect_at_risk(students)

        return AnalyticsDashboard(
            total_students=n,
            average=avg,
            median=median,
            std_dev=std_dev,
            highest=max(grades),
            lowest=min(grades),
            passing_count=passing,
            failing_count=n - passing,
            distribution=dist,
            by_major=by_major,
            gpa_average=gpa_avg,
            at_risk_count=len(at_risk),
        )

    # ── At-Risk Detection ────────────────────────────────────────────────

    # Thresholds
    _AT_RISK_GRADE: float = 65.0        # grade below this triggers a flag
    _FAILING_GRADE: float = 60.0        # hard failing threshold

    # Grade band labels (ordered A→F)
    _BANDS = ["A (90-100)", "B (80-89)", "C (70-79)", "D (60-69)", "F (<60)"]

    @staticmethod
    def _grade_band(grade: float) -> str:
        if grade >= 90:
            return "A (90-100)"
        if grade >= 80:
            return "B (80-89)"
        if grade >= 70:
            return "C (70-79)"
        if grade >= 60:
            return "D (60-69)"
        return "F (<60)"

    @staticmethod
    def detect_at_risk(students: List[Student]) -> List[AtRiskStudent]:
        """Identifies students who may need academic intervention.

        A student is flagged when ANY of the following apply:
          • Overall grade < 65
          • Academic standing is "Academic Warning" or "Academic Probation"
          • GPA is set and < 2.0
          • Any individual course grade < 60

        Args:
            students: Full student list.

        Returns:
            List of AtRiskStudent objects, sorted by grade ascending.
        """
        results: List[AtRiskStudent] = []
        for s in students:
            reasons: List[str] = []

            if s.grade < StatisticsService._AT_RISK_GRADE:
                reasons.append(f"Overall grade {s.grade} is below 65")

            standing = s.academic_standing()
            if standing in ("Academic Warning", "Academic Probation"):
                reasons.append(f"Academic standing: {standing}")

            if s.gpa is not None and s.gpa < 2.0:
                reasons.append(f"GPA {s.gpa} is below 2.0")

            failing_courses = [
                c.course for c in s.courses if c.grade is not None and c.grade < StatisticsService.PASS_THRESHOLD
            ]
            if failing_courses:
                reasons.append(f"Failing course(s): {', '.join(failing_courses)}")

            if reasons:
                results.append(AtRiskStudent(student=s, reasons=reasons))

        results.sort(key=lambda ar: ar.student.grade)
        return results
