"""
ClassRecord model — represents a shared academic class.

Contains only the data structure and its serialization.
No business logic, no I/O, no side effects.
"""

from __future__ import annotations

import math
import uuid
from datetime import date
from typing import Optional


class ClassRecord:
    """A shared academic class with scheduling and credit metadata.

    Attributes:
        _id      (str):            Stable UUID4.
        _code    (str):            Course code, e.g. "CS101".
        _title   (str):            Human-readable title.
        _term_start (date | None): First day of the term.
        _term_end   (date | None): Last day of the term.
        _credits (float):          Credit hours (must be > 0).
    """

    def __init__(
        self,
        code: str,
        title: str,
        credits: float = 3.0,
        term_start: Optional[date] = None,
        term_end: Optional[date] = None,
        class_id: Optional[str] = None,
    ) -> None:
        code = (code or "").strip()
        title = (title or "").strip()
        if not code:
            raise ValueError("Class code cannot be empty.")
        if not title:
            raise ValueError("Class title cannot be empty.")
        if isinstance(credits, bool) or not isinstance(credits, (int, float)):
            raise ValueError("Credits must be a number.")
        if math.isnan(credits) or math.isinf(credits):
            raise ValueError("Credits must be a finite number.")
        if credits <= 0:
            raise ValueError("Credits must be positive.")

        self._id: str = class_id if class_id else str(uuid.uuid4())
        self._code: str = code
        self._title: str = title
        self._credits: float = float(credits)
        self._term_start: Optional[date] = term_start
        self._term_end: Optional[date] = term_end

    # ── Properties ──────────────────────────────────────────────────────────

    @property
    def id(self) -> str:
        return self._id

    @property
    def code(self) -> str:
        return self._code

    @code.setter
    def code(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            raise ValueError("Class code cannot be empty.")
        self._code = value

    @property
    def title(self) -> str:
        return self._title

    @title.setter
    def title(self, value: str) -> None:
        value = (value or "").strip()
        if not value:
            raise ValueError("Class title cannot be empty.")
        self._title = value

    @property
    def credits(self) -> float:
        return self._credits

    @credits.setter
    def credits(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Credits must be a number.")
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Credits must be a finite number.")
        if value <= 0:
            raise ValueError("Credits must be positive.")
        self._credits = float(value)

    @property
    def term_start(self) -> Optional[date]:
        return self._term_start

    @term_start.setter
    def term_start(self, value: Optional[date]) -> None:
        self._term_start = value

    @property
    def term_end(self) -> Optional[date]:
        return self._term_end

    @term_end.setter
    def term_end(self, value: Optional[date]) -> None:
        self._term_end = value

    # ── Serialization ────────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "code": self._code,
            "title": self._title,
            "credits": self._credits,
            "term_start": self._term_start.isoformat() if self._term_start else None,
            "term_end": self._term_end.isoformat() if self._term_end else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ClassRecord":
        term_start = None
        term_end = None
        raw_start = data.get("term_start")
        raw_end = data.get("term_end")
        if raw_start:
            term_start = date.fromisoformat(raw_start)
        if raw_end:
            term_end = date.fromisoformat(raw_end)
        return cls(
            code=data["code"],
            title=data["title"],
            credits=data.get("credits", 3.0),
            term_start=term_start,
            term_end=term_end,
            class_id=data.get("id"),
        )

    # ── Dunder Methods ───────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"ClassRecord(code='{self._code}', title='{self._title}', id='{self._id}')"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, ClassRecord):
            return NotImplemented
        return self._id == other._id
