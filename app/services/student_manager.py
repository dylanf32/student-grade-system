"""
StudentManager — core CRUD service for managing students.

This service owns the in-memory student list and delegates
persistence to an injected storage backend (Dependency Injection).
It contains NO print statements — all user-facing output is
handled by the UI layer.
"""

from __future__ import annotations

import threading
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
        self._lock: threading.Lock = threading.Lock()

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
        with self._lock:
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
        with self._lock:
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
        valid, msg = InputValidator.validate_grade(new_grade)
        if not valid:
            raise ValueError(msg)

        with self._lock:
            valid, msg = InputValidator.validate_index(index, len(self._students))
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
        with self._lock:
            valid, msg = InputValidator.validate_index(index, len(self._students))
            if not valid:
                raise ValueError(msg)
            return self._students.pop(index)

    # ═══════════════════════════════════════════════════════════════════════
    #  Search
    # ═══════════════════════════════════════════════════════════════════════

    def search_by_name(self, name: str) -> int:
        """Case-insensitive search by student name.

        Returns the index of the **first** match for backward compatibility
        with callers that expect a single-integer result.  Use
        ``search_all_by_name`` when you need all matches.

        Args:
            name: The name to look for (leading/trailing whitespace ignored).

        Returns:
            Index of the first match, or -1 if not found.
        """
        target = name.strip().lower()
        with self._lock:
            for i, student in enumerate(self._students):
                if student.name.lower() == target:
                    return i
        return -1

    def search_all_by_name(self, name: str) -> list:
        """Case-insensitive search returning ALL matching students.

        Because names are not unique identifiers, multiple students may
        share the same name.  This method returns every match so callers
        can present all of them for the user to choose from.

        Args:
            name: The name to look for (leading/trailing whitespace ignored).

        Returns:
            List of ``(index, student)`` tuples for all exact matches,
            ordered by their position in the list.  Empty list if none found.
        """
        target = name.strip().lower()
        with self._lock:
            return [
                (i, s)
                for i, s in enumerate(self._students)
                if s.name.lower() == target
            ]

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
        with self._lock:
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
        """Persists current data via the storage backend.

        Returns:
            True on success.
        """
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
