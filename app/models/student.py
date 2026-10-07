"""
Student model — represents a single student entity.

This module contains ONLY the data structure and its serialization.
No business logic, no I/O, no side effects.
"""

from __future__ import annotations

import math
import uuid

from app.config import MIN_GRADE, MAX_GRADE


class Student:
    """Immutable-name student entity with a mutable grade and a stable UUID.

    Attributes:
        _id    (str): Stable UUID4 that never changes after creation.
        _name  (str): Student's full name (stripped, non-empty).
        _grade (float): Numeric grade in [MIN_GRADE, MAX_GRADE].
    """

    # ── Construction ─────────────────────────────────────────────────────

    def __init__(self, name: str, grade: float, student_id: str | None = None) -> None:
        """Create a new Student.

        Args:
            name:       Non-empty student name.
            grade:      Numeric grade in [MIN_GRADE, MAX_GRADE].  Decimals
                        are preserved (85.5 is stored as 85.5, not 85).
            student_id: Optional existing UUID string.  If omitted a new
                        UUID4 is generated automatically.  Pass an existing
                        value only when deserialising from storage so that
                        stable identity is preserved across restarts.

        Raises:
            ValueError: If name is blank or grade is out of range.
        """
        if not name or not name.strip():
            raise ValueError("Student name cannot be empty.")
        # Reject non-numeric types and Python booleans (bool subclasses int).
        if isinstance(grade, bool) or not isinstance(grade, (int, float)):
            raise ValueError("Grade must be a number.")
        # Reject NaN and infinity — they pass isinstance checks but are invalid.
        if math.isnan(grade) or math.isinf(grade):
            raise ValueError("Grade must be a finite number.")
        if grade < MIN_GRADE or grade > MAX_GRADE:
            raise ValueError(
                f"Grade must be between {MIN_GRADE} and {MAX_GRADE}."
            )

        self._id: str = student_id if student_id else str(uuid.uuid4())
        self._name: str = name.strip()
        # Store as float; use int only when the value has no fractional part.
        self._grade: float = float(grade)

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def id(self) -> str:
        """Returns the student's stable UUID (read-only)."""
        return self._id

    @property
    def name(self) -> str:
        """Returns the student's name (read-only)."""
        return self._name

    @property
    def grade(self) -> float:
        """Returns the student's grade."""
        return self._grade

    @grade.setter
    def grade(self, value: float) -> None:
        """Sets the student's grade with validation.

        Args:
            value: New grade in [MIN_GRADE, MAX_GRADE].

        Raises:
            ValueError: If value is out of range or not a finite number.
        """
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Grade must be a number.")
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Grade must be a finite number.")
        if value < MIN_GRADE or value > MAX_GRADE:
            raise ValueError(
                f"Grade must be between {MIN_GRADE} and {MAX_GRADE}."
            )
        self._grade = float(value)

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Converts this Student to a plain dictionary.

        Returns:
            ``{"id": str, "name": str, "grade": float}``
        """
        return {"id": self._id, "name": self._name, "grade": self._grade}

    @classmethod
    def from_dict(cls, data: dict) -> Student:
        """Factory: builds a Student from a dictionary.

        Backward-compatible: existing JSON records without an ``id`` key
        are silently assigned a fresh UUID so legacy data is never lost.

        Args:
            data: Dict with ``name`` and ``grade`` keys, and optionally
                  an ``id`` key.

        Returns:
            A new Student instance.

        Raises:
            ValueError: If required keys are missing or values are invalid.
        """
        try:
            name = data["name"]
            grade = data["grade"]
        except (KeyError, TypeError) as exc:
            raise ValueError(
                f"Student record is missing required field: {exc}"
            ) from exc
        return cls(
            name=name,
            grade=grade,
            student_id=data.get("id"),  # None → auto-generate
        )

    # ── Dunder Methods ───────────────────────────────────────────────────

    def __str__(self) -> str:
        return f"{self._name} (Grade: {self._grade})"

    def __repr__(self) -> str:
        return f"Student(name='{self._name}', grade={self._grade}, id='{self._id}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Student):
            return NotImplemented
        return self._id == other._id
