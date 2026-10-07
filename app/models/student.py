"""
Student model — represents a single student entity.

This module contains ONLY the data structure and its serialization.
No business logic, no I/O, no side effects.
"""

from __future__ import annotations

import math
import uuid
from typing import List

from app.config import MIN_GRADE, MAX_GRADE


# ---------------------------------------------------------------------------
# Course record helper
# ---------------------------------------------------------------------------

class CourseGrade:
    """A single course with its associated grade."""

    def __init__(self, course: str, grade: float | None = None) -> None:
        if not course or not course.strip():
            raise ValueError("Course name cannot be empty.")
        self.course: str = course.strip()
        self.grade: float | None = grade

    def to_dict(self) -> dict:
        return {"course": self.course, "grade": self.grade}

    @classmethod
    def from_dict(cls, data: dict) -> "CourseGrade":
        return cls(course=data["course"], grade=data.get("grade"))

    def __repr__(self) -> str:
        return f"CourseGrade(course='{self.course}', grade={self.grade})"


# ---------------------------------------------------------------------------
# Student
# ---------------------------------------------------------------------------

class Student:
    """Student entity with full academic profile and a stable UUID.

    Attributes:
        _id            (str):                 Stable UUID4.
        _name          (str):                 Full name.
        _grade         (float):               Overall/primary grade [MIN_GRADE, MAX_GRADE].
        _email         (str):                 Contact email (optional).
        _major         (str):                 Program/major (optional).
        _academic_year (str):                 e.g. "Freshman", "Sophomore", "1", "2".
        _gpa           (float | None):        Cumulative GPA (0.0–4.0, optional).
        _courses       (List[CourseGrade]):   Enrolled courses with individual grades.
        _notes         (str):                 Free-text academic notes/status.
    """

    # ── Construction ─────────────────────────────────────────────────────

    def __init__(
        self,
        name: str,
        grade: float,
        student_id: str | None = None,
        email: str = "",
        major: str = "",
        academic_year: str = "",
        gpa: float | None = None,
        courses: List[CourseGrade] | None = None,
        notes: str = "",
    ) -> None:
        if not name or not name.strip():
            raise ValueError("Student name cannot be empty.")
        if isinstance(grade, bool) or not isinstance(grade, (int, float)):
            raise ValueError("Grade must be a number.")
        if math.isnan(grade) or math.isinf(grade):
            raise ValueError("Grade must be a finite number.")
        if grade < MIN_GRADE or grade > MAX_GRADE:
            raise ValueError(f"Grade must be between {MIN_GRADE} and {MAX_GRADE}.")

        self._id: str = student_id if student_id else str(uuid.uuid4())
        self._name: str = name.strip()
        self._grade: float = float(grade)
        self._email: str = email.strip() if email else ""
        self._major: str = major.strip() if major else ""
        self._academic_year: str = academic_year.strip() if academic_year else ""
        self._gpa: float | None = gpa
        self._courses: List[CourseGrade] = courses if courses is not None else []
        self._notes: str = notes.strip() if notes else ""

    # ── Properties ───────────────────────────────────────────────────────

    @property
    def id(self) -> str:
        return self._id

    @property
    def name(self) -> str:
        return self._name

    @property
    def grade(self) -> float:
        return self._grade

    @grade.setter
    def grade(self, value: float) -> None:
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("Grade must be a number.")
        if math.isnan(value) or math.isinf(value):
            raise ValueError("Grade must be a finite number.")
        if value < MIN_GRADE or value > MAX_GRADE:
            raise ValueError(f"Grade must be between {MIN_GRADE} and {MAX_GRADE}.")
        self._grade = float(value)

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str) -> None:
        self._email = value.strip() if value else ""

    @property
    def major(self) -> str:
        return self._major

    @major.setter
    def major(self, value: str) -> None:
        self._major = value.strip() if value else ""

    @property
    def academic_year(self) -> str:
        return self._academic_year

    @academic_year.setter
    def academic_year(self, value: str) -> None:
        self._academic_year = value.strip() if value else ""

    @property
    def gpa(self) -> float | None:
        return self._gpa

    @gpa.setter
    def gpa(self, value: float | None) -> None:
        if value is not None:
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError("GPA must be a number.")
            if math.isnan(value) or math.isinf(value):
                raise ValueError("GPA must be a finite number.")
            if value < 0.0 or value > 4.0:
                raise ValueError("GPA must be between 0.0 and 4.0.")
        self._gpa = value

    @property
    def courses(self) -> List[CourseGrade]:
        return list(self._courses)

    @courses.setter
    def courses(self, value: List[CourseGrade]) -> None:
        self._courses = value if value is not None else []

    @property
    def notes(self) -> str:
        return self._notes

    @notes.setter
    def notes(self, value: str) -> None:
        self._notes = value.strip() if value else ""

    # ── Computed helpers ─────────────────────────────────────────────────

    def compute_gpa_from_courses(self) -> float | None:
        """Computes a 4.0-scale GPA from enrolled courses that have grades.

        Uses the simple percentage→4.0 mapping:
          A 90–100 → 4.0, B 80–89 → 3.0, C 70–79 → 2.0, D 60–69 → 1.0, F <60 → 0.0
        Returns None when no graded courses exist.
        """
        graded = [c for c in self._courses if c.grade is not None]
        if not graded:
            return None
        total = 0.0
        for c in graded:
            g = c.grade
            if g >= 90:
                total += 4.0
            elif g >= 80:
                total += 3.0
            elif g >= 70:
                total += 2.0
            elif g >= 60:
                total += 1.0
            # else 0.0
        return round(total / len(graded), 2)

    def academic_standing(self) -> str:
        """Returns a human-readable academic standing based on GPA."""
        gpa = self._gpa
        if gpa is None:
            gpa_calc = self.compute_gpa_from_courses()
            if gpa_calc is None:
                # Fall back to overall grade
                gpa_calc = self._grade / 25.0  # 100 → 4.0 scale
            gpa = gpa_calc
        if gpa >= 3.5:
            return "Dean's List"
        if gpa >= 3.0:
            return "Good Standing"
        if gpa >= 2.0:
            return "Satisfactory"
        if gpa >= 1.0:
            return "Academic Warning"
        return "Academic Probation"

    # ── Serialization ────────────────────────────────────────────────────

    def to_dict(self) -> dict:
        return {
            "id": self._id,
            "name": self._name,
            "grade": self._grade,
            "email": self._email,
            "major": self._major,
            "academic_year": self._academic_year,
            "gpa": self._gpa,
            "courses": [c.to_dict() for c in self._courses],
            "notes": self._notes,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Student":
        """Factory: builds a Student from a dictionary.

        Backward-compatible: existing records missing new fields are silently
        given sensible defaults so legacy data is never lost.
        """
        try:
            name = data["name"]
            grade = data["grade"]
        except (KeyError, TypeError) as exc:
            raise ValueError(f"Student record is missing required field: {exc}") from exc

        raw_courses = data.get("courses") or []
        courses = []
        for c in raw_courses:
            try:
                courses.append(CourseGrade.from_dict(c))
            except (KeyError, ValueError):
                pass  # skip malformed course entries

        return cls(
            name=name,
            grade=grade,
            student_id=data.get("id"),
            email=data.get("email", ""),
            major=data.get("major", ""),
            academic_year=data.get("academic_year", ""),
            gpa=data.get("gpa"),
            courses=courses,
            notes=data.get("notes", ""),
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
