"""
Input validation utilities.

Centralizes all validation logic so that both the service layer
and the UI layer can reuse the same rules without duplication.
"""

import math
from typing import Tuple

from app.config import MIN_GRADE, MAX_GRADE


class InputValidator:
    """Static validation methods for user inputs."""

    @staticmethod
    def validate_name(name: str) -> Tuple[bool, str]:
        """Validates a student name.

        Args:
            name: The name string to validate.

        Returns:
            Tuple of (is_valid, error_message).
            error_message is empty when valid.
        """
        if not name or not name.strip():
            return False, "Name cannot be empty."
        if len(name.strip()) < 2:
            return False, "Name must be at least 2 characters long."
        if any(ch.isdigit() for ch in name):
            return False, "Name should not contain numbers."
        return True, ""

    @staticmethod
    def validate_grade(grade: float) -> Tuple[bool, str]:
        """Validates a grade value.

        Accepts int or float in [MIN_GRADE, MAX_GRADE].
        Rejects booleans, NaN, and infinity.

        Args:
            grade: The numeric grade to validate.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if isinstance(grade, bool) or not isinstance(grade, (int, float)):
            return False, "Grade must be a number."
        if math.isnan(grade) or math.isinf(grade):
            return False, "Grade must be a finite number."
        if grade < MIN_GRADE or grade > MAX_GRADE:
            return False, f"Grade must be between {MIN_GRADE} and {MAX_GRADE}."
        return True, ""

    @staticmethod
    def validate_index(index: int, list_size: int) -> Tuple[bool, str]:
        """Validates a list index.

        Args:
            index:     The index to validate.
            list_size: The current size of the list.

        Returns:
            Tuple of (is_valid, error_message).
        """
        if list_size == 0:
            return False, "The student list is empty."
        if not isinstance(index, int):
            return False, "Index must be an integer."
        if index < 0 or index >= list_size:
            return False, f"Index out of range. Valid range: 0 to {list_size - 1}."
        return True, ""
