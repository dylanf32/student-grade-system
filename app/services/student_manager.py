"""
StudentManager — core CRUD service for managing students.

This service owns the in-memory student list and delegates
persistence to an injected storage backend (Dependency Injection).
It contains NO print statements — all user-facing output is
handled by the UI layer.
"""

from __future__ import annotations

from typing import List, Optional

from app.models.student import Student
from app.storage.base_storage import BaseStorage
from app.validators.input_validator import InputValidator


class StudentManager:
    """Manages a collection of Students with CRUD, search, and sort.

    Attributes:
        _students (List[Student]): In-memory list of students.
        _storage  (BaseStorage):   Injected persistence backend.
    """

    def __init__(self, storage: BaseStorage) -> None:
        """Initialize the manager with a storage backend.

        Args:
            storage: Any concrete implementation of BaseStorage.
        """
        self._students: List[Student] = []
        self._storage: BaseStorage = storage

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Create
    # ═══════════════════════════════════════════════════════════════════════

    def add_student(self, name: str, grade: int) -> Student:
        """Creates and appends a new Student.

        Args:
            name:  Student name (validated).
            grade: Student grade (validated).

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

        student = Student(name, grade)
        self._students.append(student)
        return student

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Read
    # ═══════════════════════════════════════════════════════════════════════

    def get_student(self, index: int) -> Optional[Student]:
        """Returns the student at the given index.

        Args:
            index: 0-based index.

        Returns:
            Student object, or None if index is invalid.
        """
        valid, _ = InputValidator.validate_index(index, self.size())
        if not valid:
            return None
        return self._students[index]

    def get_all_students(self) -> List[Student]:
        """Returns a shallow copy of the student list.

        Returns:
            List of Student objects.
        """
        return list(self._students)

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Update
    # ═══════════════════════════════════════════════════════════════════════

    def update_grade(self, index: int, new_grade: int) -> Student:
        """Updates the grade of the student at ``index``.

        Args:
            index:     0-based index of the target student.
            new_grade: New grade value.

        Returns:
            The updated Student object.

        Raises:
            ValueError: If index or grade is invalid.
        """
        valid, msg = InputValidator.validate_index(index, self.size())
        if not valid:
            raise ValueError(msg)

        valid, msg = InputValidator.validate_grade(new_grade)
        if not valid:
            raise ValueError(msg)

        self._students[index].grade = new_grade
        return self._students[index]

    # ═══════════════════════════════════════════════════════════════════════
    #  CRUD — Delete
    # ═══════════════════════════════════════════════════════════════════════

    def remove_student(self, index: int) -> Student:
        """Removes and returns the student at ``index``.

        Args:
            index: 0-based index of the student to remove.

        Returns:
            The removed Student object.

        Raises:
            ValueError: If index is invalid.
        """
        valid, msg = InputValidator.validate_index(index, self.size())
        if not valid:
            raise ValueError(msg)
        return self._students.pop(index)

    # ═══════════════════════════════════════════════════════════════════════
    #  Search
    # ═══════════════════════════════════════════════════════════════════════

    def search_by_name(self, name: str) -> int:
        """Case-insensitive search by student name.

        Args:
            name: The name to look for.

        Returns:
            Index of the first match, or -1 if not found.
        """
        target = name.strip().lower()
        for i, student in enumerate(self._students):
            if student.name.lower() == target:
                return i
        return -1

    # ═══════════════════════════════════════════════════════════════════════
    #  Sort
    # ═══════════════════════════════════════════════════════════════════════

    def sort_by_grade(self, ascending: bool = True) -> List[Student]:
        """Sorts the internal list by grade (in-place).

        Args:
            ascending: True for low→high, False for high→low.

        Returns:
            The sorted list (same reference).
        """
        self._students.sort(
            key=lambda s: s.grade,
            reverse=not ascending,
        )
        return self._students

    # ═══════════════════════════════════════════════════════════════════════
    #  Utility
    # ═══════════════════════════════════════════════════════════════════════

    def size(self) -> int:
        """Returns the number of students."""
        return len(self._students)

    def is_empty(self) -> bool:
        """Returns True if no students are stored."""
        return len(self._students) == 0

    # ═══════════════════════════════════════════════════════════════════════
    #  Persistence (delegates to storage backend)
    # ═══════════════════════════════════════════════════════════════════════

    def save(self) -> bool:
        """Persists current data via the storage backend.

        Returns:
            True on success.
        """
        return self._storage.save(self._students)

    def load(self) -> int:
        """Loads data from the storage backend.

        Returns:
            Number of students loaded.
        """
        self._students = self._storage.load()
        return len(self._students)
