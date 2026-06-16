"""
Abstract base class for storage backends.

Defines the contract that every storage implementation must follow.
This allows swapping JSON for SQLite, CSV, or any other backend
without touching the service layer — just provide a new subclass.
"""

from abc import ABC, abstractmethod
from typing import List

from app.models.student import Student


class BaseStorage(ABC):
    """Abstract interface for student data persistence.

    Subclasses must implement ``save`` and ``load``.
    """

    @abstractmethod
    def save(self, students: List[Student]) -> bool:
        """Persist the list of students.

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
