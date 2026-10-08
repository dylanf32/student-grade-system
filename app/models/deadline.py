"""
Deadline model — represents an assignment or exam deadline.

This module contains ONLY the data structure and its serialization.
No business logic, no I/O, no side effects.
"""

from __future__ import annotations

import uuid
from typing import Optional


class Deadline:
    """A single assignment or exam deadline.

    Attributes:
        _id          (str):           Stable UUID4.
        _title       (str):           Descriptive title (e.g. "Midterm Exam").
        _type        (str):           "assignment" | "exam" | "project" | "other".
        _due_date    (str):           ISO-8601 date string YYYY-MM-DD.
        _course      (str):           Associated course name (optional).
        _description (str):           Free-text description (optional).
        _student_id  (str | None):    UUID of linked student, or None for class-wide.
    """

    VALID_TYPES = {"assignment", "exam", "project", "other"}

    def __init__(
        self,
        title: str,
        due_date: str,
        deadline_type: str = "assignment",
        course: str = "",
        description: str = "",
        student_id: Optional[str] = None,
        deadline_id: Optional[str] = None,
    ) -> None:
        if not title or not title.strip():
            raise ValueError("Deadline title cannot be empty.")
        if not due_date or not due_date.strip():
            raise ValueError("Due date cannot be empty.")
        if deadline_type not in self.VALID_TYPES:
            deadline_type = "other"

        self._id: str = deadline_id if deadline_id else str(uuid.uuid4())
        self._title: str = title.strip()
        self._type: str = deadline_type
        self._due_date: str = due_date.strip()
        self._course: str = course.strip() if course else ""
        self._description: str = description.strip() if description else ""
        self._student_id: Optional[str] = student_id

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def id(self) -> str:
        return self._id

    @property
    def title(self) -> str:
        return self._title

    @property
    def type(self) -> str:
        return self._type

    @property
    def due_date(self) -> str:
        return self._due_date

    @property
    def course(self) -> str:
        return self._course

    @property
    def description(self) -> str:
        return self._description

    @property
    def student_id(self) -> Optional[str]:
        return self._student_id

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "title": self._title,
            "type": self._type,
            "due_date": self._due_date,
            "course": self._course,
            "description": self._description,
            "student_id": self._student_id,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Deadline":
        return cls(
            title=data["title"],
            due_date=data["due_date"],
            deadline_type=data.get("type", "assignment"),
            course=data.get("course", ""),
            description=data.get("description", ""),
            student_id=data.get("student_id"),
            deadline_id=data.get("id"),
        )

    def __repr__(self) -> str:
        return f"Deadline(title='{self._title}', due='{self._due_date}', type='{self._type}')"
