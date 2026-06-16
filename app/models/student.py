"""
Student model — represents a single student entity.

This module contains ONLY the data structure and its serialization.
No business logic, no I/O, no side effects.
"""

from __future__ import annotations

from app.config import MIN_GRADE, MAX_GRADE


class Student:
    """Immutable-name student entity with a mutable grade.

    Attributes:
        _name (str):  Student's full name (stripped, non-empty).
        _grade (int): Numeric grade in [MIN_GRADE, MAX_GRADE].
    """

    # ── Construction ─────────────────────────────────────────────────────

    def __init__(self, name: str, grade: int) -> None:
        """Create a new Student.

        Args:
            name:  Non-empty student name.
            grade: Integer grade in [MIN_GRADE, MAX_GRADE].

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

        self._name: str = name.strip()
        self._grade: int = int(grade)

    # ── Properties ───────────────────────────────────────────────────────

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
            ``{"name": str, "grade": int}``
        """
        return {"name": self._name, "grade": self._grade}

    @classmethod
    def from_dict(cls, data: dict) -> Student:
        """Factory: builds a Student from a dictionary.

        Args:
            data: Dict with ``name`` and ``grade`` keys.

        Returns:
            A new Student instance.
        """
        return cls(name=data["name"], grade=data["grade"])

    # ── Dunder Methods ───────────────────────────────────────────────────

    def __str__(self) -> str:
        return f"{self._name} (Grade: {self._grade})"

    def __repr__(self) -> str:
        return f"Student(name='{self._name}', grade={self._grade})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Student):
            return NotImplemented
        return self._name == other._name and self._grade == other._grade
