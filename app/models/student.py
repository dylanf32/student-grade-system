"""
Student model — represents a single student entity.

This module contains ONLY the data structure and its serialization.
No business logic, no I/O, no side effects.
"""

from __future__ import annotations

import uuid

from app.config import MIN_GRADE, MAX_GRADE


class Student:
    """Immutable-name student entity with a mutable grade and a stable UUID.

    Attributes:
        _id    (str): Stable UUID4 that never changes after creation.
        _name  (str): Student's full name (stripped, non-empty).
        _grade (int): Numeric grade in [MIN_GRADE, MAX_GRADE].
    """

    # ── Construction ─────────────────────────────────────────────────────

    def __init__(self, name: str, grade: int, student_id: str | None = None) -> None:
        """Create a new Student.

        Args:
            name:       Non-empty student name.
            grade:      Integer grade in [MIN_GRADE, MAX_GRADE].
            student_id: Optional existing UUID string.  If omitted a new
                        UUID4 is generated automatically.  Pass an existing
                        value only when deserialising from storage so that
                        stable identity is preserved across restarts.

        Raises:
            ValueError: If name is blank or grade is out of range.
        """
        if not name or not name.strip():
            raise ValueError("Student name cannot be empty.")
        if not isinstance(grade, (int, float)):
            raise ValueError("Grade must be a number.")
        if grade < MIN_GRADE or grade > MAX_GRADE:
            raise ValueError(
                f"Grade must be between {MIN_GRADE} and {MAX_GRADE}."
            )

        self._id: str = student_id if student_id else str(uuid.uuid4())
        self._name: str = name.strip()
        self._grade: int = int(grade)

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
    def grade(self) -> int:
        """Returns the student's grade."""
        return self._grade

    @grade.setter
    def grade(self, value: int) -> None:
        """Sets the student's grade with validation.

        Args:
            value: New grade in [MIN_GRADE, MAX_GRADE].

        Raises:
            ValueError: If value is out of range.
        """
        if not isinstance(value, (int, float)):
            raise ValueError("Grade must be a number.")
        if value < MIN_GRADE or value > MAX_GRADE:
            raise ValueError(
                f"Grade must be between {MIN_GRADE} and {MAX_GRADE}."
            )
        self._grade = int(value)

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        """Converts this Student to a plain dictionary.

        Returns:
            ``{"id": str, "name": str, "grade": int}``
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
        """
        return cls(
            name=data["name"],
            grade=data["grade"],
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
        return self._name == other._name and self._grade == other._grade
