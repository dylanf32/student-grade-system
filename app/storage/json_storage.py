"""
JSON file storage backend.

Implements BaseStorage using a simple JSON file.
"""

import json
import os
from typing import List

from app.config import DEFAULT_DATA_FILE
from app.models.student import Student
from app.storage.base_storage import BaseStorage


class JsonStorage(BaseStorage):
    """Persists student data to a local JSON file.

    Attributes:
        _file_path (str): Absolute path to the JSON file.
    """

    def __init__(self, file_path: str | None = None) -> None:
        """Initialize the JSON storage backend.

        Args:
            file_path: Path to the JSON file.
                       Defaults to ``config.DEFAULT_DATA_FILE``.
        """
        self._file_path: str = file_path or DEFAULT_DATA_FILE

    @property
    def file_path(self) -> str:
        """Returns the path being used for storage."""
        return self._file_path

    # ── BaseStorage Implementation ───────────────────────────────────────

    def save(self, students: List[Student]) -> bool:
        """Writes all students to the JSON file.

        Args:
            students: List of Student objects.

        Returns:
            True on success, False on failure.
        """
        try:
            os.makedirs(os.path.dirname(self._file_path), exist_ok=True)
            data = [s.to_dict() for s in students]
            with open(self._file_path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=4, ensure_ascii=False)
            return True
        except (IOError, OSError) as exc:
            print(f"  [Storage Error] Could not save: {exc}")
            return False

    def load(self) -> List[Student]:
        """Reads students from the JSON file.

        Returns:
            List of Student objects, or empty list on failure / missing file.
        """
        if not os.path.exists(self._file_path):
            return []

        try:
            with open(self._file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            return [Student.from_dict(entry) for entry in data]
        except (IOError, json.JSONDecodeError, KeyError, ValueError) as exc:
            print(f"  [Storage Error] Could not load: {exc}")
            return []
