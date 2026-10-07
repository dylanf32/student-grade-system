"""
JSON file storage backend.

Implements BaseStorage using a simple JSON file.
"""

import json
import os
import tempfile
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
        """Atomically writes all students to the JSON file.

        Writes to a temporary file in the same directory first, flushes
        and syncs it to disk, then uses os.replace() to atomically swap
        it over the original.  The original file is never truncated or
        removed until the replacement is fully written, so a crash at
        any point leaves the previous data intact.

        Args:
            students: List of Student objects.

        Returns:
            True on success, False on failure.
        """
        target_dir = os.path.dirname(self._file_path)
        # dirname is empty when file_path is a bare filename; use "." so
        # makedirs and NamedTemporaryFile both have a real directory.
        if not target_dir:
            target_dir = "."
        tmp_path: str | None = None
        try:
            os.makedirs(target_dir, exist_ok=True)
            data = [s.to_dict() for s in students]

            # Write to a sibling temp file so os.replace stays on the
            # same filesystem (required for atomicity on most OSes).
            fd, tmp_path = tempfile.mkstemp(
                dir=target_dir, suffix=".tmp", prefix=".students_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(data, fh, indent=4, ensure_ascii=False)
                    fh.flush()
                    os.fsync(fh.fileno())
            except Exception:
                # fd is already closed by the context manager on exception,
                # but we still need to clean up the temp file.
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise

            # Atomic replacement — original is untouched until this succeeds.
            os.replace(tmp_path, self._file_path)
            tmp_path = None  # ownership transferred; no cleanup needed
            return True
        except Exception as exc:
            print(f"  [Storage Error] Could not save: {exc}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
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
