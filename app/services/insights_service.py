"""
InsightsService — derives read-only per-student support flags.

Stateless: receives the student list as an argument.
Reuses the passing threshold from config.py so the same policy
applies here as in StatisticsService.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from app.config import PASSING_THRESHOLD
from app.models.student import Student


@dataclass(frozen=True)
class StudentInsight:
    """Support flag for one student.

    Attributes:
        student_id: Stable UUID of the student.
        name:       Student name (for display convenience).
        grade:      Current overall grade.
        threshold:  The passing threshold used for evaluation.
        status:     "needs_attention" when grade < threshold, else "passing".
        reason:     Human-readable explanation of the flag.
    """

    student_id: str
    name: str
    grade: float
    threshold: int
    status: str
    reason: str


class InsightsService:
    """Produces read-only per-student support flags.

    The only rule: a student whose overall grade is below the shared
    PASSING_THRESHOLD is flagged as "needs_attention" with a factual reason.
    Students at or above the threshold are flagged as "passing".

    This service is intentionally minimal — it wraps the same threshold
    constant used by StatisticsService to guarantee a consistent policy.
    """

    @staticmethod
    def get_insights(students: List[Student]) -> List[StudentInsight]:
        """Derive support flags for every student.

        Args:
            students: Full student list (order is preserved).

        Returns:
            List of StudentInsight objects, one per student,
            sorted by grade ascending so below-threshold students appear first.
        """
        insights: List[StudentInsight] = []
        for s in students:
            if s.grade < PASSING_THRESHOLD:
                status = "needs_attention"
                reason = (
                    f"Current grade {s.grade} is below passing threshold {PASSING_THRESHOLD}."
                )
            else:
                status = "passing"
                reason = (
                    f"Current grade {s.grade} meets or exceeds passing threshold {PASSING_THRESHOLD}."
                )
            insights.append(StudentInsight(
                student_id=s.id,
                name=s.name,
                grade=s.grade,
                threshold=PASSING_THRESHOLD,
                status=status,
                reason=reason,
            ))

        # Below-threshold students first, then by grade ascending within each group.
        insights.sort(key=lambda i: (0 if i.status == "needs_attention" else 1, i.grade))
        return insights
