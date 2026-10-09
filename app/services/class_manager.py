"""
ClassManager — service for managing shared classes and student/class enrollments.

Enrollments are stored as a set of (student_id, class_id) pairs.
The manager prevents duplicate enrollments and dangling references,
and rejects deleting a class that still has enrolled students.
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Set, Tuple

from app.models.class_record import ClassRecord


class ClassManager:
    """Manages a collection of ClassRecord objects and student enrollments.

    Attributes:
        _classes     (Dict[str, ClassRecord]):  class_id → ClassRecord.
        _enrollments (Set[Tuple[str, str]]):     (student_id, class_id) pairs.
        _lock        (threading.Lock):           Guards concurrent access.
    """

    def __init__(self) -> None:
        self._classes: Dict[str, ClassRecord] = {}
        self._enrollments: Set[Tuple[str, str]] = set()
        self._lock = threading.Lock()

    # ══════════════════════════════════════════════════════════════════════════
    #  Class CRUD
    # ══════════════════════════════════════════════════════════════════════════

    def add_class(
        self,
        code: str,
        title: str,
        credits: float = 3.0,
        term_start=None,
        term_end=None,
    ) -> ClassRecord:
        """Creates and stores a new ClassRecord.

        Args:
            code:       Course code (non-empty).
            title:      Course title (non-empty).
            credits:    Credit hours (positive).
            term_start: Optional start date.
            term_end:   Optional end date.

        Returns:
            The newly created ClassRecord.

        Raises:
            ValueError: If code/title/credits are invalid.
        """
        record = ClassRecord(
            code=code,
            title=title,
            credits=credits,
            term_start=term_start,
            term_end=term_end,
        )
        with self._lock:
            self._classes[record.id] = record
        return record

    def get_class(self, class_id: str) -> Optional[ClassRecord]:
        """Returns the ClassRecord with the given UUID, or None."""
        with self._lock:
            return self._classes.get(class_id)

    def get_all_classes(self) -> List[ClassRecord]:
        """Returns all classes as a list (insertion order not guaranteed)."""
        with self._lock:
            return list(self._classes.values())

    def update_class(self, class_id: str, **fields) -> ClassRecord:
        """Updates fields on an existing class.

        Supported fields: code, title, credits, term_start, term_end.

        Raises:
            ValueError: If the class is not found or a field value is invalid.
        """
        with self._lock:
            record = self._classes.get(class_id)
            if record is None:
                raise ValueError(f"Class not found: {class_id}")
            if "code" in fields:
                record.code = fields["code"]   # setter validates
            if "title" in fields:
                record.title = fields["title"]
            if "credits" in fields:
                record.credits = fields["credits"]
            if "term_start" in fields:
                record.term_start = fields["term_start"]
            if "term_end" in fields:
                record.term_end = fields["term_end"]
            return record

    def delete_class(self, class_id: str) -> ClassRecord:
        """Removes a class.

        Raises:
            ValueError: If the class is not found or has enrolled students.
        """
        with self._lock:
            record = self._classes.get(class_id)
            if record is None:
                raise ValueError(f"Class not found: {class_id}")
            dependents = [sid for (sid, cid) in self._enrollments if cid == class_id]
            if dependents:
                raise ValueError(
                    f"Cannot delete class '{record.code}': "
                    f"{len(dependents)} student(s) still enrolled."
                )
            del self._classes[class_id]
        return record

    # ══════════════════════════════════════════════════════════════════════════
    #  Enrollment management
    # ══════════════════════════════════════════════════════════════════════════

    def enroll(self, student_id: str, class_id: str) -> None:
        """Enrolls a student in a class (idempotent).

        Args:
            student_id: UUID of the student.
            class_id:   UUID of the class.

        Raises:
            ValueError: If the class does not exist.
        """
        with self._lock:
            if class_id not in self._classes:
                raise ValueError(f"Class not found: {class_id}")
            self._enrollments.add((student_id, class_id))

    def unenroll(self, student_id: str, class_id: str) -> None:
        """Removes a student's enrollment in a class (idempotent).

        Args:
            student_id: UUID of the student.
            class_id:   UUID of the class.

        Raises:
            ValueError: If the class does not exist.
        """
        with self._lock:
            if class_id not in self._classes:
                raise ValueError(f"Class not found: {class_id}")
            self._enrollments.discard((student_id, class_id))

    def remove_all_enrollments_for_student(self, student_id: str) -> None:
        """Removes all enrollments for a given student (called on student delete)."""
        with self._lock:
            self._enrollments = {
                (sid, cid) for (sid, cid) in self._enrollments if sid != student_id
            }

    def get_classes_for_student(self, student_id: str) -> List[ClassRecord]:
        """Returns all classes a student is enrolled in."""
        with self._lock:
            class_ids = {cid for (sid, cid) in self._enrollments if sid == student_id}
            return [self._classes[cid] for cid in class_ids if cid in self._classes]

    def get_students_in_class(self, class_id: str) -> List[str]:
        """Returns the student UUIDs enrolled in a given class."""
        with self._lock:
            return [sid for (sid, cid) in self._enrollments if cid == class_id]

    def is_enrolled(self, student_id: str, class_id: str) -> bool:
        """Returns True if the student is enrolled in the class."""
        with self._lock:
            return (student_id, class_id) in self._enrollments

    # ══════════════════════════════════════════════════════════════════════════
    #  Serialization helpers (used by storage backends)
    # ══════════════════════════════════════════════════════════════════════════

    def classes_to_list(self) -> List[dict]:
        """Serializes all classes to a list of dicts."""
        with self._lock:
            return [c.to_dict() for c in self._classes.values()]

    def enrollments_to_list(self) -> List[dict]:
        """Serializes all enrollments to a list of dicts."""
        with self._lock:
            return [
                {"student_id": sid, "class_id": cid}
                for (sid, cid) in sorted(self._enrollments)
            ]

    def load_from_data(
        self,
        classes: List[dict],
        enrollments: List[dict],
    ) -> None:
        """Replaces the in-memory state from raw serialized data.

        Silently drops malformed entries so legacy records survive.

        Args:
            classes:     List of class dicts (from storage).
            enrollments: List of enrollment dicts (from storage).
        """
        new_classes: Dict[str, ClassRecord] = {}
        for entry in classes:
            try:
                rec = ClassRecord.from_dict(entry)
                new_classes[rec.id] = rec
            except (KeyError, ValueError):
                pass  # skip malformed class records

        new_enrollments: Set[Tuple[str, str]] = set()
        for entry in enrollments:
            sid = entry.get("student_id", "")
            cid = entry.get("class_id", "")
            if sid and cid and cid in new_classes:
                new_enrollments.add((sid, cid))
            # silently drop enrollments referencing unknown classes

        with self._lock:
            self._classes = new_classes
            self._enrollments = new_enrollments
