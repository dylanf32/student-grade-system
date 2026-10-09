"""
Abstract base class for storage backends.

Defines the contract that every storage implementation must follow.
This allows swapping JSON for SQLite, CSV, or any other backend
without touching the service layer — just provide a new subclass.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Set, Tuple

from app.models.student import Student


class BaseStorage(ABC):
    """Abstract interface for student data persistence.

    Subclasses must implement ``save`` and ``load`` (students only, legacy
    interface) as well as ``save_dataset`` and ``load_dataset`` (full dataset
    including classes and enrollments, introduced in format version 2).
    """

    @abstractmethod
    def save(self, students: List[Student]) -> bool:
        """Persist the list of students (students only, legacy interface).

        Args:
            students: The list of Student objects to save.

        Returns:
            True on success, False on failure.
        """
        ...

    @abstractmethod
    def load(self) -> List[Student]:
        """Load and return the list of students.

        Returns:
            A list of Student objects (empty list if nothing stored).
        """
        ...

    def save_dataset(
        self,
        students: List[Student],
        classes: List[dict],
        enrollments: List[dict],
    ) -> bool:
        """Persist the complete dataset (students, classes, enrollments).

        Default implementation delegates to ``save`` for backward
        compatibility.  Storage backends that support the full schema
        should override this method.

        Args:
            students:    List of Student objects.
            classes:     Serialized class dicts.
            enrollments: Serialized enrollment dicts.

        Returns:
            True on success, False on failure.
        """
        return self.save(students)

    def load_dataset(self) -> "DatasetPayload":
        """Load the complete dataset.

        Default implementation loads students only (classes/enrollments
        empty), preserving compatibility with legacy backends.

        Returns:
            A DatasetPayload namedtuple with ``students``, ``classes``,
            and ``enrollments`` fields.
        """
        return DatasetPayload(students=self.load(), classes=[], enrollments=[])


# ---------------------------------------------------------------------------
# Lightweight container for the full dataset returned by load_dataset()
# ---------------------------------------------------------------------------

class DatasetPayload:
    """Holds all data loaded by ``BaseStorage.load_dataset``.

    Attributes:
        students:          List of Student objects.
        classes:           Serialized class dicts (from ClassRecord.to_dict).
        enrollments:       Serialized enrollment dicts.
        categories:        Serialized Category dicts (A2).
        enrollment_grades: Serialized EnrollmentGrade dicts (A2).
    """

    __slots__ = ("students", "classes", "enrollments", "categories", "enrollment_grades")

    def __init__(
        self,
        students: List[Student],
        classes: List[dict],
        enrollments: List[dict],
        categories: List[dict] | None = None,
        enrollment_grades: List[dict] | None = None,
    ) -> None:
        self.students = students
        self.classes = classes
        self.enrollments = enrollments
        self.categories: List[dict] = categories if categories is not None else []
        self.enrollment_grades: List[dict] = enrollment_grades if enrollment_grades is not None else []
