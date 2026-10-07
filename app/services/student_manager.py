"""
StudentManager — core CRUD service for managing students.

This service owns the in-memory student list and delegates
persistence to an injected storage backend (Dependency Injection).
It contains NO print statements — all user-facing output is
handled by the UI layer.
"""

from __future__ import annotations

import csv
import io
import threading
from typing import List, Optional, Tuple

from app.models.student import Student, CourseGrade
from app.storage.base_storage import BaseStorage
from app.validators.input_validator import InputValidator


class StudentManager:
    """Manages a collection of Students with CRUD, search, sort, and filter.

    Attributes:
        _students (List[Student]): In-memory list of students.
        _storage  (BaseStorage):   Injected persistence backend.
        _lock     (threading.Lock): Guards concurrent access.
    """

    def __init__(self, storage: BaseStorage) -> None:
        self._students: List[Student] = []
        self._storage: BaseStorage = storage
        self._lock: threading.Lock = threading.Lock()

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Create
    # ═══════════════════════════════════════════════════════════════════════

    def add_student(
        self,
        name: str,
        grade: float,
        email: str = "",
        major: str = "",
        academic_year: str = "",
        gpa: Optional[float] = None,
        courses: Optional[List[CourseGrade]] = None,
        notes: str = "",
    ) -> Student:
        """Creates and appends a new Student.

        Args:
            name:          Student name (validated).
            grade:         Student overall grade (validated).
            email:         Contact email (optional).
            major:         Program/major (optional).
            academic_year: Year string e.g. "Freshman" (optional).
            gpa:           Cumulative GPA 0–4 (optional).
            courses:       List of CourseGrade objects (optional).
            notes:         Free-text notes (optional).

        Returns:
            The newly created Student object.

        Raises:
            ValueError: If name or grade is invalid.
        """
        valid, msg = InputValidator.validate_name(name)
        if not valid:
            raise ValueError(msg)

        valid, msg = InputValidator.validate_grade(grade)
        if not valid:
            raise ValueError(msg)

        student = Student(
            name=name,
            grade=grade,
            email=email,
            major=major,
            academic_year=academic_year,
            gpa=gpa,
            courses=courses,
            notes=notes,
        )
        with self._lock:
            self._students.append(student)
        return student

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Read
    # ═══════════════════════════════════════════════════════════════════════

    def get_student(self, index: int) -> Student:
        """Returns the student at the given index.

        Args:
            index: 0-based index.

        Raises:
            ValueError: If index is invalid.
        """
        valid, msg = InputValidator.validate_index(index, self.size())
        if not valid:
            raise ValueError(msg)
        return self._students[index]

    def get_by_id(self, student_id: str) -> Optional[Student]:
        """Returns the student with the given UUID, or None if not found."""
        with self._lock:
            for s in self._students:
                if s.id == student_id:
                    return s
        return None

    def get_all_students(self) -> List[Student]:
        """Returns a shallow copy of the student list."""
        with self._lock:
            return list(self._students)

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Update
    # ═══════════════════════════════════════════════════════════════════════

    def update_grade(self, index: int, new_grade: float) -> Student:
        """Updates the grade of the student at ``index``.

        Raises:
            ValueError: If index or grade is invalid.
        """
        valid, msg = InputValidator.validate_grade(new_grade)
        if not valid:
            raise ValueError(msg)

        with self._lock:
            valid, msg = InputValidator.validate_index(index, len(self._students))
            if not valid:
                raise ValueError(msg)
            self._students[index].grade = new_grade
            return self._students[index]

    def update_student(self, student_id: str, **fields) -> Student:
        """Updates arbitrary fields of a student identified by UUID.

        Supported fields: grade, email, major, academic_year, gpa, courses, notes.
        Fields not provided are left unchanged.

        Args:
            student_id: Stable UUID of the target student.
            **fields:   Keyword arguments for fields to update.

        Returns:
            The updated Student.

        Raises:
            ValueError: If the student is not found or a field value is invalid.
        """
        with self._lock:
            student = next((s for s in self._students if s.id == student_id), None)
            if student is None:
                raise ValueError("Student not found.")

            if "grade" in fields:
                valid, msg = InputValidator.validate_grade(fields["grade"])
                if not valid:
                    raise ValueError(msg)
                student.grade = fields["grade"]

            if "email" in fields:
                student.email = fields["email"]
            if "major" in fields:
                student.major = fields["major"]
            if "academic_year" in fields:
                student.academic_year = fields["academic_year"]
            if "gpa" in fields:
                student.gpa = fields["gpa"]  # setter validates
            if "courses" in fields:
                student.courses = fields["courses"]
            if "notes" in fields:
                student.notes = fields["notes"]

            return student

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Delete
    # ═══════════════════════════════════════════════════════════════════════

    def remove_student(self, index: int) -> Student:
        """Removes and returns the student at ``index``.

        Raises:
            ValueError: If index is invalid.
        """
        with self._lock:
            valid, msg = InputValidator.validate_index(index, len(self._students))
            if not valid:
                raise ValueError(msg)
            return self._students.pop(index)

    # ═══════════════════════════════════════════════════════════════════════
    #  Search & Filter
    # ═══════════════════════════════════════════════════════════════════════

    def search_by_name(self, name: str) -> int:
        """Case-insensitive search by student name.

        Returns the index of the **first** match, or -1 if not found.
        Use ``search_all_by_name`` when you need all matches.
        """
        target = name.strip().lower()
        with self._lock:
            for i, student in enumerate(self._students):
                if student.name.lower() == target:
                    return i
        return -1

    def search_all_by_name(self, name: str) -> List[Tuple[int, Student]]:
        """Case-insensitive search returning ALL matching students.

        Returns:
            List of ``(index, student)`` tuples for all exact matches.
        """
        target = name.strip().lower()
        with self._lock:
            return [
                (i, s)
                for i, s in enumerate(self._students)
                if s.name.lower() == target
            ]

    def filter_students(
        self,
        name: str = "",
        major: str = "",
        academic_year: str = "",
        standing: str = "",
        min_grade: Optional[float] = None,
        max_grade: Optional[float] = None,
    ) -> List[Tuple[int, Student]]:
        """Returns (index, student) pairs matching all supplied filters.

        All filters are optional and case-insensitive substring matches
        except min_grade / max_grade which are numeric bounds.
        """
        with self._lock:
            results = []
            for i, s in enumerate(self._students):
                if name and name.strip().lower() not in s.name.lower():
                    continue
                if major and major.strip().lower() not in s.major.lower():
                    continue
                if academic_year and academic_year.strip().lower() not in s.academic_year.lower():
                    continue
                if standing and standing.strip().lower() not in s.academic_standing().lower():
                    continue
                if min_grade is not None and s.grade < min_grade:
                    continue
                if max_grade is not None and s.grade > max_grade:
                    continue
                results.append((i, s))
        return results

    # ═══════════════════════════════════════════════════════════════════════
    #  Sort
    # ═══════════════════════════════════════════════════════════════════════

    def sort_by_grade(self, ascending: bool = True) -> List[Student]:
        """Sorts the internal list by grade (in-place).

        Returns:
            The sorted list (same reference).
        """
        with self._lock:
            self._students.sort(key=lambda s: s.grade, reverse=not ascending)
            return self._students

    # ═══════════════════════════════════════════════════════════════════════
    #  Utility
    # ═══════════════════════════════════════════════════════════════════════

    def size(self) -> int:
        """Returns the number of students."""
        with self._lock:
            return len(self._students)

    def is_empty(self) -> bool:
        """Returns True if no students are stored."""
        with self._lock:
            return len(self._students) == 0

    # ═══════════════════════════════════════════════════════════════════════
    #  Persistence (delegates to storage backend)
    # ═══════════════════════════════════════════════════════════════════════

    def save(self) -> bool:
        """Persists current data via the storage backend."""
        with self._lock:
            snapshot = list(self._students)
        return self._storage.save(snapshot)

    def load(self) -> int:
        """Loads data from the storage backend.

        Returns:
            Number of students loaded.
        """
        students = self._storage.load()
        with self._lock:
            self._students = students
        return len(self._students)

    # ═══════════════════════════════════════════════════════════════════════
    #  CSV Import / Export
    # ═══════════════════════════════════════════════════════════════════════

    # CSV columns: name, grade, email, major, academic_year, gpa, notes
    _CSV_FIELDS = ["name", "grade", "email", "major", "academic_year", "gpa", "notes"]

    def export_csv(self, filepath: str) -> int:
        """Writes all students to a CSV file.

        Args:
            filepath: Destination path (created or overwritten).

        Returns:
            Number of rows written.

        Raises:
            OSError: If the file cannot be written.
        """
        with self._lock:
            snapshot = list(self._students)

        with open(filepath, "w", newline="", encoding="utf-8") as fh:
            writer = csv.DictWriter(fh, fieldnames=self._CSV_FIELDS)
            writer.writeheader()
            for s in snapshot:
                writer.writerow({
                    "name": s.name,
                    "grade": s.grade,
                    "email": s.email,
                    "major": s.major,
                    "academic_year": s.academic_year,
                    "gpa": s.gpa if s.gpa is not None else "",
                    "notes": s.notes,
                })
        return len(snapshot)

    def import_csv(self, filepath: str) -> Tuple[int, List[str]]:
        """Imports students from a CSV file, appending to existing data.

        Skips rows with validation errors and collects their messages.

        Args:
            filepath: Path to a CSV file with a header row.

        Returns:
            (imported_count, list_of_error_messages)

        Raises:
            OSError: If the file cannot be read.
        """
        imported = 0
        errors: List[str] = []

        with open(filepath, newline="", encoding="utf-8") as fh:
            reader = csv.DictReader(fh)
            for line_num, row in enumerate(reader, start=2):  # 1 = header
                name = (row.get("name") or "").strip()
                raw_grade = (row.get("grade") or "").strip()

                if not name:
                    errors.append(f"Row {line_num}: missing name — skipped.")
                    continue
                try:
                    grade = float(raw_grade)
                except (ValueError, TypeError):
                    errors.append(f"Row {line_num} ({name!r}): invalid grade {raw_grade!r} — skipped.")
                    continue

                raw_gpa = (row.get("gpa") or "").strip()
                gpa: Optional[float] = None
                if raw_gpa:
                    try:
                        gpa = float(raw_gpa)
                    except ValueError:
                        gpa = None

                try:
                    self.add_student(
                        name=name,
                        grade=grade,
                        email=(row.get("email") or "").strip(),
                        major=(row.get("major") or "").strip(),
                        academic_year=(row.get("academic_year") or "").strip(),
                        gpa=gpa,
                        notes=(row.get("notes") or "").strip(),
                    )
                    imported += 1
                except ValueError as exc:
                    errors.append(f"Row {line_num} ({name!r}): {exc} — skipped.")

        return imported, errors
