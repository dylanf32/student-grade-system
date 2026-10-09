"""
Gradebook models — categories, assignments, and per-enrollment scores.

Data structures only; no I/O, no calculations.

Schema
------
  Category       — belongs to a ClassRecord; has a weight (nonneg finite)
                   and a list of Assignment objects.
  Assignment     — belongs to a Category; has a name and positive possible points.
  EnrollmentGrade — maps (student_id, class_id) to per-assignment scores.
                   A score may be null (ungraded) or a finite float 0–possible.
"""

from __future__ import annotations

import math
import uuid
from typing import Dict, List, Optional


# ── Assignment ────────────────────────────────────────────────────────────────

class Assignment:
    """A single gradeable task within a Category.

    Attributes:
        _id            (str):   Stable UUID4.
        _name          (str):   Assignment name.
        _possible      (float): Maximum achievable points (must be > 0).
    """

    def __init__(
        self,
        name: str,
        possible: float,
        assignment_id: Optional[str] = None,
    ) -> None:
        name = (name or "").strip()
        if not name:
            raise ValueError("Assignment name cannot be empty.")
        _validate_positive_finite(possible, "Possible points")
        self._id: str = assignment_id if assignment_id else str(uuid.uuid4())
        self._name: str = name
        self._possible: float = float(possible)

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            raise ValueError("Assignment name cannot be empty.")
        self._name = value

    @property
    def possible(self) -> float:
        return self._possible

    @possible.setter
    def possible(self, value: float) -> None:
        _validate_positive_finite(value, "Possible points")
        self._possible = float(value)

    def to_dict(self) -> dict:
        return {"id": self._id, "name": self._name, "possible": self._possible}

    @classmethod
    def from_dict(cls, data: dict) -> "Assignment":
        return cls(
            name=data["name"],
            possible=data["possible"],
            assignment_id=data.get("id"),
        )

    def __repr__(self) -> str:
        return f"Assignment(name='{self._name}', possible={self._possible}, id='{self._id}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Assignment):
            return NotImplemented
        return self._id == other._id


# ── Category ──────────────────────────────────────────────────────────────────

class Category:
    """A grade category within a ClassRecord (e.g. "Homework", "Exams").

    Attributes:
        _id          (str):              Stable UUID4.
        _class_id    (str):              UUID of the owning ClassRecord.
        _name        (str):              Category name.
        _weight      (float):            Weight percentage (finite, >= 0).
        _assignments (List[Assignment]): Ordered list of assignments.
    """

    def __init__(
        self,
        class_id: str,
        name: str,
        weight: float,
        assignments: Optional[List[Assignment]] = None,
        category_id: Optional[str] = None,
    ) -> None:
        if not class_id or not class_id.strip():
            raise ValueError("Category must have a class_id.")
        name = (name or "").strip()
        if not name:
            raise ValueError("Category name cannot be empty.")
        _validate_nonneg_finite(weight, "Weight")
        self._id: str = category_id if category_id else str(uuid.uuid4())
        self._class_id: str = class_id
        self._name: str = name
        self._weight: float = float(weight)
        self._assignments: List[Assignment] = list(assignments) if assignments else []

    @property
    def id(self) -> str:
        return self._id

    @property
    def class_id(self) -> str:
        return self._class_id

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            raise ValueError("Category name cannot be empty.")
        self._name = value

    @property
    def weight(self) -> float:
        return self._weight

    @weight.setter
    def weight(self, value: float) -> None:
        _validate_nonneg_finite(value, "Weight")
        self._weight = float(value)

    @property
    def assignments(self) -> List[Assignment]:
        return list(self._assignments)

    def add_assignment(self, assignment: Assignment) -> None:
        """Appends an assignment; duplicate IDs are silently skipped."""
        existing_ids = {a.id for a in self._assignments}
        if assignment.id not in existing_ids:
            self._assignments.append(assignment)

    def remove_assignment(self, assignment_id: str) -> None:
        """Removes the assignment with the given id (no-op if absent)."""
        self._assignments = [a for a in self._assignments if a.id != assignment_id]

    def get_assignment(self, assignment_id: str) -> Optional[Assignment]:
        for a in self._assignments:
            if a.id == assignment_id:
                return a
        return None

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "class_id": self._class_id,
            "name": self._name,
            "weight": self._weight,
            "assignments": [a.to_dict() for a in self._assignments],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Category":
        assignments = []
        for raw in data.get("assignments", []):
            try:
                assignments.append(Assignment.from_dict(raw))
            except (KeyError, ValueError):
                pass  # skip malformed
        return cls(
            class_id=data["class_id"],
            name=data["name"],
            weight=data["weight"],
            assignments=assignments,
            category_id=data.get("id"),
        )

    def __repr__(self) -> str:
        return (
            f"Category(name='{self._name}', weight={self._weight}, "
            f"class_id='{self._class_id}', id='{self._id}')"
        )

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Category):
            return NotImplemented
        return self._id == other._id


# ── EnrollmentGrade ───────────────────────────────────────────────────────────

class EnrollmentGrade:
    """Stores per-assignment scores for one (student, class) enrollment.

    Scores are keyed by assignment UUID.
    A score of None means the assignment has not been graded yet.
    A score of 0.0 is a valid, graded zero.

    Attributes:
        _student_id (str):                  UUID of the student.
        _class_id   (str):                  UUID of the class.
        _scores     (Dict[str, float|None]): assignment_id → score.
    """

    def __init__(self, student_id: str, class_id: str) -> None:
        if not student_id:
            raise ValueError("EnrollmentGrade requires a student_id.")
        if not class_id:
            raise ValueError("EnrollmentGrade requires a class_id.")
        self._student_id: str = student_id
        self._class_id: str = class_id
        self._scores: Dict[str, Optional[float]] = {}

    @property
    def student_id(self) -> str:
        return self._student_id

    @property
    def class_id(self) -> str:
        return self._class_id

    def set_score(
        self, assignment_id: str, score: Optional[float], possible: float
    ) -> None:
        """Record or update a score.

        Args:
            assignment_id: UUID of the assignment.
            score:         Numeric score (0 – possible) or None for ungraded.
            possible:      Maximum points for this assignment (used for validation).

        Raises:
            ValueError: If score is a boolean, non-finite, or out of [0, possible].
        """
        if score is not None:
            if isinstance(score, bool):
                raise ValueError("Score must not be a boolean.")
            if not isinstance(score, (int, float)):
                raise ValueError("Score must be a number or null.")
            if math.isnan(score) or math.isinf(score):
                raise ValueError("Score must be a finite number.")
            if score < 0:
                raise ValueError("Score cannot be negative.")
            if score > possible:
                raise ValueError(
                    f"Score {score} exceeds possible points {possible}."
                )
            score = float(score)
        self._scores[assignment_id] = score

    def get_score(self, assignment_id: str) -> Optional[float]:
        """Returns the score for the given assignment_id, or None if unset."""
        return self._scores.get(assignment_id)

    def to_dict(self) -> dict:
        return {
            "student_id": self._student_id,
            "class_id": self._class_id,
            "scores": {aid: s for aid, s in self._scores.items()},
        }

    @classmethod
    def from_dict(cls, data: dict) -> "EnrollmentGrade":
        obj = cls(student_id=data["student_id"], class_id=data["class_id"])
        for aid, score in data.get("scores", {}).items():
            obj._scores[aid] = float(score) if score is not None else None
        return obj

    def __repr__(self) -> str:
        return (
            f"EnrollmentGrade(student_id='{self._student_id}', "
            f"class_id='{self._class_id}', scores={len(self._scores)})"
        )


# ── Internal validators ───────────────────────────────────────────────────────

def _validate_positive_finite(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number.")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{label} must be finite.")
    if value <= 0:
        raise ValueError(f"{label} must be positive.")


def _validate_nonneg_finite(value: float, label: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{label} must be a number.")
    if math.isnan(value) or math.isinf(value):
        raise ValueError(f"{label} must be finite.")
    if value < 0:
        raise ValueError(f"{label} must be non-negative.")
