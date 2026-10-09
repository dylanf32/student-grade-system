"""
Tests for A1 — Classes and enrollments.

Covers:
  - ClassRecord construction and validation
  - ClassManager CRUD and duplicate/dangling-reference guards
  - Enrollment add/remove/query
  - JsonStorage legacy (v1) loading — students survive, classes/enrollments empty
  - JsonStorage new-format (v2) round trip — all three collections survive
"""

from __future__ import annotations

import json
import os
import tempfile
import uuid
from datetime import date

import pytest

from app.models.class_record import ClassRecord
from app.models.student import Student
from app.services.class_manager import ClassManager
from app.storage.base_storage import DatasetPayload
from app.storage.json_storage import JsonStorage


# ══════════════════════════════════════════════════════════════════════════════
#  ClassRecord — construction and validation
# ══════════════════════════════════════════════════════════════════════════════

class TestClassRecordConstruction:
    def test_basic_construction(self):
        rec = ClassRecord(code="CS101", title="Intro to CS", credits=3.0)
        assert rec.code == "CS101"
        assert rec.title == "Intro to CS"
        assert rec.credits == 3.0
        assert rec.id  # UUID assigned

    def test_stable_id_round_trip(self):
        fixed_id = str(uuid.uuid4())
        rec = ClassRecord(code="MA201", title="Calculus", class_id=fixed_id)
        assert rec.id == fixed_id

    def test_empty_code_raises(self):
        with pytest.raises(ValueError, match="code"):
            ClassRecord(code="", title="Title")

    def test_empty_title_raises(self):
        with pytest.raises(ValueError, match="title"):
            ClassRecord(code="CS101", title="")

    def test_zero_credits_raises(self):
        with pytest.raises(ValueError, match="positive"):
            ClassRecord(code="CS101", title="T", credits=0)

    def test_negative_credits_raises(self):
        with pytest.raises(ValueError, match="positive"):
            ClassRecord(code="CS101", title="T", credits=-1)

    def test_boolean_credits_raises(self):
        with pytest.raises(ValueError):
            ClassRecord(code="CS101", title="T", credits=True)

    def test_term_dates(self):
        start = date(2025, 1, 13)
        end = date(2025, 5, 10)
        rec = ClassRecord(code="CS101", title="T", term_start=start, term_end=end)
        assert rec.term_start == start
        assert rec.term_end == end

    def test_to_dict_from_dict_round_trip(self):
        start = date(2025, 1, 13)
        end = date(2025, 5, 10)
        rec = ClassRecord(code="CS101", title="Intro", credits=4.0, term_start=start, term_end=end)
        d = rec.to_dict()
        rec2 = ClassRecord.from_dict(d)
        assert rec2.id == rec.id
        assert rec2.code == rec.code
        assert rec2.title == rec.title
        assert rec2.credits == rec.credits
        assert rec2.term_start == start
        assert rec2.term_end == end

    def test_from_dict_no_dates(self):
        d = {"id": str(uuid.uuid4()), "code": "ART100", "title": "Art"}
        rec = ClassRecord.from_dict(d)
        assert rec.term_start is None
        assert rec.term_end is None
        assert rec.credits == 3.0  # default

    def test_equality_by_id(self):
        fixed = str(uuid.uuid4())
        r1 = ClassRecord(code="CS101", title="T", class_id=fixed)
        r2 = ClassRecord(code="CS101", title="T", class_id=fixed)
        assert r1 == r2

    def test_inequality_different_id(self):
        r1 = ClassRecord(code="CS101", title="T")
        r2 = ClassRecord(code="CS101", title="T")
        assert r1 != r2


# ══════════════════════════════════════════════════════════════════════════════
#  ClassManager — CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestClassManagerCRUD:
    def setup_method(self):
        self.mgr = ClassManager()

    def test_add_and_get(self):
        rec = self.mgr.add_class("CS101", "Intro to CS")
        assert self.mgr.get_class(rec.id) is rec

    def test_get_unknown_returns_none(self):
        assert self.mgr.get_class("nonexistent") is None

    def test_get_all(self):
        self.mgr.add_class("CS101", "A")
        self.mgr.add_class("MA201", "B")
        assert len(self.mgr.get_all_classes()) == 2

    def test_update_class(self):
        rec = self.mgr.add_class("CS101", "Old Title")
        updated = self.mgr.update_class(rec.id, title="New Title", credits=4.0)
        assert updated.title == "New Title"
        assert updated.credits == 4.0

    def test_update_unknown_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.mgr.update_class("ghost", title="X")

    def test_update_invalid_credits_raises(self):
        rec = self.mgr.add_class("CS101", "T")
        with pytest.raises(ValueError, match="positive"):
            self.mgr.update_class(rec.id, credits=0)

    def test_delete_class_no_enrollments(self):
        rec = self.mgr.add_class("CS101", "T")
        deleted = self.mgr.delete_class(rec.id)
        assert deleted.id == rec.id
        assert self.mgr.get_class(rec.id) is None

    def test_delete_class_with_enrollments_raises(self):
        rec = self.mgr.add_class("CS101", "T")
        student_id = str(uuid.uuid4())
        self.mgr.enroll(student_id, rec.id)
        with pytest.raises(ValueError, match="enrolled"):
            self.mgr.delete_class(rec.id)

    def test_delete_unknown_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.mgr.delete_class("ghost")


# ══════════════════════════════════════════════════════════════════════════════
#  ClassManager — Enrollments
# ══════════════════════════════════════════════════════════════════════════════

class TestClassManagerEnrollments:
    def setup_method(self):
        self.mgr = ClassManager()
        self.cls = self.mgr.add_class("CS101", "Intro")
        self.sid = str(uuid.uuid4())

    def test_enroll(self):
        self.mgr.enroll(self.sid, self.cls.id)
        assert self.mgr.is_enrolled(self.sid, self.cls.id)

    def test_enroll_idempotent(self):
        self.mgr.enroll(self.sid, self.cls.id)
        self.mgr.enroll(self.sid, self.cls.id)  # second call is a no-op
        assert len(self.mgr.get_students_in_class(self.cls.id)) == 1

    def test_enroll_unknown_class_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.mgr.enroll(self.sid, "ghost")

    def test_unenroll(self):
        self.mgr.enroll(self.sid, self.cls.id)
        self.mgr.unenroll(self.sid, self.cls.id)
        assert not self.mgr.is_enrolled(self.sid, self.cls.id)

    def test_unenroll_idempotent(self):
        # unenrolling someone not enrolled should not raise
        self.mgr.unenroll(self.sid, self.cls.id)
        assert not self.mgr.is_enrolled(self.sid, self.cls.id)

    def test_unenroll_unknown_class_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.mgr.unenroll(self.sid, "ghost")

    def test_get_classes_for_student(self):
        cls2 = self.mgr.add_class("MA201", "Calc")
        self.mgr.enroll(self.sid, self.cls.id)
        self.mgr.enroll(self.sid, cls2.id)
        ids = {c.id for c in self.mgr.get_classes_for_student(self.sid)}
        assert ids == {self.cls.id, cls2.id}

    def test_get_students_in_class(self):
        sid2 = str(uuid.uuid4())
        self.mgr.enroll(self.sid, self.cls.id)
        self.mgr.enroll(sid2, self.cls.id)
        enrolled = set(self.mgr.get_students_in_class(self.cls.id))
        assert enrolled == {self.sid, sid2}

    def test_remove_all_enrollments_for_student(self):
        cls2 = self.mgr.add_class("MA201", "Calc")
        self.mgr.enroll(self.sid, self.cls.id)
        self.mgr.enroll(self.sid, cls2.id)
        self.mgr.remove_all_enrollments_for_student(self.sid)
        assert self.mgr.get_classes_for_student(self.sid) == []

    def test_two_students_same_class(self):
        """A class can have multiple students enrolled without confusion."""
        sid2 = str(uuid.uuid4())
        self.mgr.enroll(self.sid, self.cls.id)
        self.mgr.enroll(sid2, self.cls.id)
        assert self.mgr.is_enrolled(self.sid, self.cls.id)
        assert self.mgr.is_enrolled(sid2, self.cls.id)
        # Unenrolling one doesn't affect the other
        self.mgr.unenroll(self.sid, self.cls.id)
        assert not self.mgr.is_enrolled(self.sid, self.cls.id)
        assert self.mgr.is_enrolled(sid2, self.cls.id)

    def test_cannot_delete_class_with_student(self):
        self.mgr.enroll(self.sid, self.cls.id)
        with pytest.raises(ValueError, match="enrolled"):
            self.mgr.delete_class(self.cls.id)
        # unenroll then delete succeeds
        self.mgr.unenroll(self.sid, self.cls.id)
        self.mgr.delete_class(self.cls.id)
        assert self.mgr.get_class(self.cls.id) is None


# ══════════════════════════════════════════════════════════════════════════════
#  JsonStorage — legacy (v1) load
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonStorageLegacyLoad:
    """load_dataset on a v1 (bare array) file must not lose student data."""

    def _write_v1(self, path: str, students: list[dict]) -> None:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(students, f)

    def test_legacy_students_preserved(self, tmp_path):
        p = str(tmp_path / "students.json")
        original = [
            {"id": str(uuid.uuid4()), "name": "Alice", "grade": 88.0},
            {"id": str(uuid.uuid4()), "name": "Bob",   "grade": 72.5},
        ]
        self._write_v1(p, original)

        storage = JsonStorage(file_path=p)
        payload = storage.load_dataset()

        names = {s.name for s in payload.students}
        assert names == {"Alice", "Bob"}
        assert payload.classes == []
        assert payload.enrollments == []

    def test_legacy_student_uuid_preserved(self, tmp_path):
        p = str(tmp_path / "students.json")
        fixed_id = str(uuid.uuid4())
        self._write_v1(p, [{"id": fixed_id, "name": "Carol", "grade": 91.0}])

        storage = JsonStorage(file_path=p)
        payload = storage.load_dataset()

        assert payload.students[0].id == fixed_id

    def test_legacy_load_via_load_method(self, tmp_path):
        """The .load() method must also transparently handle v1."""
        p = str(tmp_path / "students.json")
        self._write_v1(p, [{"id": str(uuid.uuid4()), "name": "Dave", "grade": 65.0}])

        storage = JsonStorage(file_path=p)
        students = storage.load()
        assert len(students) == 1
        assert students[0].name == "Dave"

    def test_legacy_missing_optional_fields_use_defaults(self, tmp_path):
        """Legacy records with only name+grade must load without error."""
        p = str(tmp_path / "students.json")
        self._write_v1(p, [{"name": "Eve", "grade": 55.0}])

        storage = JsonStorage(file_path=p)
        payload = storage.load_dataset()
        s = payload.students[0]
        assert s.name == "Eve"
        assert s.notes == ""
        assert s.courses == []


# ══════════════════════════════════════════════════════════════════════════════
#  JsonStorage — v2 new-format round trip
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonStorageV2RoundTrip:
    def _build_students(self) -> list[Student]:
        return [
            Student(name="Alice", grade=90.0, student_id=str(uuid.uuid4())),
            Student(name="Bob",   grade=75.0, student_id=str(uuid.uuid4())),
        ]

    def _build_class_manager(self, students: list[Student]) -> ClassManager:
        mgr = ClassManager()
        c1 = mgr.add_class("CS101", "Intro to CS", credits=3.0,
                            term_start=date(2025, 1, 13),
                            term_end=date(2025, 5, 10))
        c2 = mgr.add_class("MA201", "Calculus", credits=4.0)
        mgr.enroll(students[0].id, c1.id)
        mgr.enroll(students[0].id, c2.id)
        mgr.enroll(students[1].id, c1.id)
        return mgr

    def test_full_round_trip(self, tmp_path):
        p = str(tmp_path / "dataset.json")
        storage = JsonStorage(file_path=p)

        students = self._build_students()
        class_mgr = self._build_class_manager(students)

        ok = storage.save_dataset(
            students=students,
            classes=class_mgr.classes_to_list(),
            enrollments=class_mgr.enrollments_to_list(),
        )
        assert ok

        payload = storage.load_dataset()

        # Students
        assert len(payload.students) == 2
        loaded_names = {s.name for s in payload.students}
        assert loaded_names == {"Alice", "Bob"}
        # UUIDs preserved
        orig_ids = {s.id for s in students}
        loaded_ids = {s.id for s in payload.students}
        assert orig_ids == loaded_ids

        # Classes
        assert len(payload.classes) == 2
        loaded_codes = {c["code"] for c in payload.classes}
        assert loaded_codes == {"CS101", "MA201"}

        # Enrollments
        assert len(payload.enrollments) == 3

        # Reload into a fresh ClassManager
        new_mgr = ClassManager()
        new_mgr.load_from_data(payload.classes, payload.enrollments)
        assert len(new_mgr.get_all_classes()) == 2
        alice = next(s for s in payload.students if s.name == "Alice")
        alice_classes = {c.code for c in new_mgr.get_classes_for_student(alice.id)}
        assert alice_classes == {"CS101", "MA201"}

    def test_term_dates_survive_round_trip(self, tmp_path):
        p = str(tmp_path / "dataset.json")
        storage = JsonStorage(file_path=p)

        mgr = ClassManager()
        cls = mgr.add_class("CS101", "T", term_start=date(2025, 1, 13), term_end=date(2025, 5, 10))
        ok = storage.save_dataset(students=[], classes=mgr.classes_to_list(), enrollments=[])
        assert ok

        payload = storage.load_dataset()
        new_mgr = ClassManager()
        new_mgr.load_from_data(payload.classes, payload.enrollments)
        loaded = new_mgr.get_class(cls.id)
        assert loaded is not None
        assert loaded.term_start == date(2025, 1, 13)
        assert loaded.term_end == date(2025, 5, 10)

    def test_json_file_has_version_key(self, tmp_path):
        p = str(tmp_path / "dataset.json")
        storage = JsonStorage(file_path=p)
        storage.save_dataset(students=[], classes=[], enrollments=[])
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        assert raw.get("version") >= 2  # v2 introduced the version key; currently v3

    def test_legacy_save_still_works(self, tmp_path):
        """storage.save() must still produce a valid bare array that storage.load() can read."""
        p = str(tmp_path / "students.json")
        storage = JsonStorage(file_path=p)
        sid = str(uuid.uuid4())
        students = [Student(name="Frank", grade=80.0, student_id=sid)]
        ok = storage.save(students)
        assert ok

        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        assert isinstance(raw, list)  # v1 format

        loaded = storage.load()
        assert len(loaded) == 1
        assert loaded[0].id == sid

    def test_malformed_class_entry_skipped(self, tmp_path):
        """A malformed class dict must be skipped; valid ones survive."""
        p = str(tmp_path / "dataset.json")
        storage = JsonStorage(file_path=p)

        mgr = ClassManager()
        mgr.add_class("CS101", "Good Class")
        classes = mgr.classes_to_list()
        classes.append({"bad": "entry"})   # missing code/title

        storage.save_dataset(students=[], classes=classes, enrollments=[])
        payload = storage.load_dataset()

        new_mgr = ClassManager()
        new_mgr.load_from_data(payload.classes, payload.enrollments)
        assert len(new_mgr.get_all_classes()) == 1
        assert new_mgr.get_all_classes()[0].code == "CS101"

    def test_dangling_enrollment_skipped(self, tmp_path):
        """Enrollments referencing a missing class UUID must be silently dropped."""
        p = str(tmp_path / "dataset.json")
        storage = JsonStorage(file_path=p)

        mgr = ClassManager()
        cls = mgr.add_class("CS101", "T")
        sid = str(uuid.uuid4())
        mgr.enroll(sid, cls.id)
        enrollments = mgr.enrollments_to_list()
        enrollments.append({"student_id": sid, "class_id": "ghost-uuid"})

        storage.save_dataset(students=[], classes=mgr.classes_to_list(), enrollments=enrollments)
        payload = storage.load_dataset()

        new_mgr = ClassManager()
        new_mgr.load_from_data(payload.classes, payload.enrollments)
        # only the valid enrollment survives
        assert len(new_mgr.get_students_in_class(cls.id)) == 1
        assert new_mgr.is_enrolled(sid, cls.id)
