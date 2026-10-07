"""
StatisticsService — computes aggregate statistics on student grades.

Separated from StudentManager so that stats logic can grow
independently (e.g., median, standard deviation, grade distribution)
without bloating the CRUD service.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

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
