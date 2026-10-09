"""
JSON file storage backend.

Implements BaseStorage using a simple JSON file.

Format versions
---------------
  v1 (legacy): The file is a bare JSON array of student dicts.
  v2:          The file is a JSON object:
               {
                 "version": 2,
                 "students": [...],
                 "classes": [...],
                 "enrollments": [...]
               }
  v3:          Adds "categories" and "enrollment_grades" arrays.
               {
                 "version": 3,
                 "students": [...],
                 "classes": [...],
                 "enrollments": [...],
                 "categories": [...],
                 "enrollment_grades": [...]
               }
  load() and load_dataset() transparently handle all formats.
  save() still writes the legacy array format so it remains compatible
  with any code that only calls save/load.
  save_dataset() always writes v3 format.
"""

import json
import os
import tempfile
from typing import List

from app.config import DEFAULT_DATA_FILE
from app.models.student import Student
from app.storage.base_storage import BaseStorage, DatasetPayload

_FORMAT_VERSION = 3


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

    # ── Internal atomic-write helper ─────────────────────────────────────

    def _atomic_write(self, payload: object) -> bool:
        """Serialize ``payload`` to JSON and atomically replace ``_file_path``.

        Returns True on success, False on any failure.
        """
        target_dir = os.path.dirname(self._file_path) or "."
        tmp_path: str | None = None
        try:
            os.makedirs(target_dir, exist_ok=True)
            fd, tmp_path = tempfile.mkstemp(
                dir=target_dir, suffix=".tmp", prefix=".students_"
            )
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as fh:
                    json.dump(payload, fh, indent=4, ensure_ascii=False)
                    fh.flush()
                    os.fsync(fh.fileno())
            except Exception:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise
            os.replace(tmp_path, self._file_path)
            tmp_path = None
            return True
        except Exception as exc:
            print(f"  [Storage Error] Could not save: {exc}")
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            return False

    # ── BaseStorage Implementation ───────────────────────────────────────

    def save(self, students: List[Student]) -> bool:
        """Atomically writes students to the JSON file in legacy array format.

        Args:
            students: List of Student objects.

        Returns:
            True on success, False on failure.
        """
        return self._atomic_write([s.to_dict() for s in students])

    def load(self) -> List[Student]:
        """Reads students from the JSON file (handles both v1 and v2 format).

        Returns:
            List of Student objects, or empty list on failure / missing file.
        """
        return self.load_dataset().students

    # ── Dataset (v2) implementation ──────────────────────────────────────

    def save_dataset(
        self,
        students: List[Student],
        classes: List[dict],
        enrollments: List[dict],
        categories: List[dict] | None = None,
        enrollment_grades: List[dict] | None = None,
    ) -> bool:
        """Atomically writes the full v3 dataset to the JSON file.

        Args:
            students:          List of Student objects.
            classes:           Serialized class dicts.
            enrollments:       Serialized enrollment dicts.
            categories:        Serialized Category dicts (A2; optional).
            enrollment_grades: Serialized EnrollmentGrade dicts (A2; optional).

        Returns:
            True on success, False on failure.
        """
        payload = {
            "version": _FORMAT_VERSION,
            "students": [s.to_dict() for s in students],
            "classes": classes,
            "enrollments": enrollments,
            "categories": categories if categories is not None else [],
            "enrollment_grades": enrollment_grades if enrollment_grades is not None else [],
        }
        return self._atomic_write(payload)

    def load_dataset(self) -> DatasetPayload:
        """Reads the full dataset, transparently handling v1, v2, and v3 formats.

        v1 (bare array):  returns students only; classes/enrollments/gradebook empty.
        v2 (version=2):   returns students, classes, enrollments; gradebook empty.
        v3 (version=3):   returns all five collections.

        Returns:
            DatasetPayload on success; empty payload on missing file or error.
        """
        if not os.path.exists(self._file_path):
            return DatasetPayload(students=[], classes=[], enrollments=[])

        try:
            with open(self._file_path, "r", encoding="utf-8") as fh:
                raw = json.load(fh)
        except (IOError, json.JSONDecodeError) as exc:
            print(f"  [Storage Error] Could not load: {exc}")
            return DatasetPayload(students=[], classes=[], enrollments=[])

        # ── Detect format ────────────────────────────────────────────────
        if isinstance(raw, list):
            # v1: bare array of student dicts
            students = _parse_students(raw)
            return DatasetPayload(students=students, classes=[], enrollments=[])

        if isinstance(raw, dict):
            version = raw.get("version", 1)
            students = _parse_students(raw.get("students", []))
            if version >= 2:
                classes = raw.get("classes", [])
                enrollments = raw.get("enrollments", [])
            else:
                classes = []
                enrollments = []
            if version >= 3:
                categories = raw.get("categories", [])
                enrollment_grades = raw.get("enrollment_grades", [])
            else:
                categories = []
                enrollment_grades = []
            return DatasetPayload(
                students=students,
                classes=classes,
                enrollments=enrollments,
                categories=categories,
                enrollment_grades=enrollment_grades,
            )

        # Unknown format — return empty
        print("  [Storage Error] Unrecognised JSON structure; returning empty dataset.")
        return DatasetPayload(students=[], classes=[], enrollments=[])


# ── Module-level helper ──────────────────────────────────────────────────────

def _parse_students(raw_list: list) -> List[Student]:
    """Converts a list of raw dicts to Student objects, skipping malformed entries."""
    students = []
    for entry in raw_list:
        try:
            students.append(Student.from_dict(entry))
        except (KeyError, ValueError) as exc:
            print(f"  [Storage Warning] Skipping malformed student record: {exc}")
    return students
