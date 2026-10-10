"""
Tests for A6 — Class selector and enrollment UI.

Covers:
  - /api/classes CRUD (create, list, update, delete)
  - /api/enrollments (enroll, unenroll, stale-response guard)
  - /api/classes/<id>/students roster endpoint
  - Two classes sharing a student
  - Delete blocked when students enrolled
  - Persistence across reload (SqliteStorage save_dataset / load_dataset)
  - Stale response guard: class switching returns correct enrolled set
"""

from __future__ import annotations

import json
import sqlite3
import unittest
import tempfile
import os

from run_web import app as flask_app, manager, class_manager, storage, _save_dataset


class TestClassesApiBase(unittest.TestCase):
    """Base: create a fresh test client backed by an in-memory SQLite database."""

    def setUp(self):
        from app.storage.sqlite_storage import SqliteStorage
        from app.storage.base_storage import DatasetPayload

        flask_app.config["TESTING"] = True
        self.client = flask_app.test_client()

        # Replace storage with an in-memory db for isolation
        self._orig_storage = manager._storage
        mem_storage = SqliteStorage(":memory:")
        # Wire the module-level storage reference
        import run_web
        run_web.storage = mem_storage
        manager._storage = mem_storage
        manager._students = []
        class_manager._classes = {}
        class_manager._enrollments = set()

    def tearDown(self):
        import run_web
        run_web.storage = self._orig_storage
        manager._storage = self._orig_storage
        # Reset in-memory state
        manager._students = []
        class_manager._classes = {}
        class_manager._enrollments = set()

    # ── helpers ──────────────────────────────────────────────────────────

    def _add_student(self, name="Alice", grade=80):
        res = self.client.post(
            "/api/students",
            json={"name": name, "grade": grade},
            content_type="application/json",
        )
        data = json.loads(res.data)
        return data["student"]["student_id"]

    def _add_class(self, code="CS101", title="Intro CS", credits=3.0):
        res = self.client.post(
            "/api/classes",
            json={"code": code, "title": title, "credits": credits},
            content_type="application/json",
        )
        data = json.loads(res.data)
        return data["class"]["id"]

    def _enroll(self, student_id, class_id):
        return self.client.post(
            "/api/enrollments",
            json={"student_id": student_id, "class_id": class_id},
            content_type="application/json",
        )

    def _unenroll(self, student_id, class_id):
        return self.client.delete(
            "/api/enrollments",
            json={"student_id": student_id, "class_id": class_id},
            content_type="application/json",
        )


# ══════════════════════════════════════════════════════════════════════════════
#  Class CRUD
# ══════════════════════════════════════════════════════════════════════════════

class TestClassCRUD(TestClassesApiBase):

    def test_list_empty(self):
        res = self.client.get("/api/classes")
        self.assertEqual(res.status_code, 200)
        self.assertEqual(json.loads(res.data), [])

    def test_create_class(self):
        res = self.client.post(
            "/api/classes",
            json={"code": "MA201", "title": "Calculus I", "credits": 4.0},
            content_type="application/json",
        )
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["class"]["code"], "MA201")
        self.assertEqual(data["class"]["credits"], 4.0)

    def test_create_duplicate_code_allowed(self):
        """ClassManager does not block duplicate codes — only duplicate UUIDs."""
        self._add_class("CS101", "Intro CS")
        res = self.client.post(
            "/api/classes",
            json={"code": "CS101", "title": "Other Section"},
            content_type="application/json",
        )
        self.assertEqual(json.loads(res.data)["success"], True)

    def test_create_missing_code(self):
        res = self.client.post(
            "/api/classes",
            json={"title": "No Code Class"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_create_missing_title(self):
        res = self.client.post(
            "/api/classes",
            json={"code": "CS101"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 400)

    def test_update_class(self):
        cid = self._add_class("CS101", "Old Title")
        res = self.client.put(
            f"/api/classes/{cid}",
            json={"title": "New Title"},
            content_type="application/json",
        )
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertEqual(data["class"]["title"], "New Title")

    def test_update_nonexistent_class(self):
        res = self.client.put(
            "/api/classes/does-not-exist",
            json={"title": "X"},
            content_type="application/json",
        )
        self.assertEqual(res.status_code, 404)

    def test_delete_empty_class(self):
        cid = self._add_class()
        res = self.client.delete(f"/api/classes/{cid}")
        self.assertEqual(json.loads(res.data)["success"], True)
        self.assertEqual(json.loads(self.client.get("/api/classes").data), [])

    def test_delete_class_with_students_blocked(self):
        sid = self._add_student()
        cid = self._add_class()
        self._enroll(sid, cid)
        res = self.client.delete(f"/api/classes/{cid}")
        self.assertEqual(res.status_code, 400)
        err = json.loads(res.data)["error"]
        self.assertIn("enrolled", err.lower())

    def test_student_count_in_payload(self):
        sid = self._add_student()
        cid = self._add_class()
        self._enroll(sid, cid)
        classes = json.loads(self.client.get("/api/classes").data)
        self.assertEqual(classes[0]["student_count"], 1)


# ══════════════════════════════════════════════════════════════════════════════
#  Enrollment
# ══════════════════════════════════════════════════════════════════════════════

class TestEnrollment(TestClassesApiBase):

    def test_enroll_student(self):
        sid = self._add_student()
        cid = self._add_class()
        res = self._enroll(sid, cid)
        self.assertTrue(json.loads(res.data)["success"])
        self.assertTrue(class_manager.is_enrolled(sid, cid))

    def test_enroll_idempotent(self):
        sid = self._add_student()
        cid = self._add_class()
        self._enroll(sid, cid)
        res = self._enroll(sid, cid)  # second call — should succeed silently
        self.assertTrue(json.loads(res.data)["success"])

    def test_unenroll_student(self):
        sid = self._add_student()
        cid = self._add_class()
        self._enroll(sid, cid)
        res = self._unenroll(sid, cid)
        self.assertTrue(json.loads(res.data)["success"])
        self.assertFalse(class_manager.is_enrolled(sid, cid))

    def test_enroll_unknown_student_404(self):
        cid = self._add_class()
        res = self._enroll("ghost-uuid", cid)
        self.assertEqual(res.status_code, 404)

    def test_enroll_unknown_class_400(self):
        sid = self._add_student()
        res = self._enroll(sid, "ghost-class-uuid")
        self.assertEqual(res.status_code, 400)

    def test_two_classes_share_student(self):
        """One student can be enrolled in two different classes simultaneously."""
        sid  = self._add_student("Bob")
        cid1 = self._add_class("CS101", "Intro CS")
        cid2 = self._add_class("MA201", "Calculus")
        self._enroll(sid, cid1)
        self._enroll(sid, cid2)

        self.assertTrue(class_manager.is_enrolled(sid, cid1))
        self.assertTrue(class_manager.is_enrolled(sid, cid2))

        roster1 = json.loads(self.client.get(f"/api/classes/{cid1}/students").data)
        roster2 = json.loads(self.client.get(f"/api/classes/{cid2}/students").data)
        ids1 = {s["student_id"] for s in roster1}
        ids2 = {s["student_id"] for s in roster2}
        self.assertIn(sid, ids1)
        self.assertIn(sid, ids2)

    def test_class_roster_excludes_unenrolled(self):
        """Roster must not contain students from a different class (stale-response guard)."""
        sid1 = self._add_student("Alice")
        sid2 = self._add_student("Eve")
        cid1 = self._add_class("CS101", "Intro CS")
        cid2 = self._add_class("CS201", "Data Structures")
        self._enroll(sid1, cid1)
        self._enroll(sid2, cid2)

        roster1 = json.loads(self.client.get(f"/api/classes/{cid1}/students").data)
        ids1 = {s["student_id"] for s in roster1}
        self.assertIn(sid1, ids1)
        self.assertNotIn(sid2, ids1)  # sid2 only in cid2


# ══════════════════════════════════════════════════════════════════════════════
#  Persistence — save_dataset / load_dataset round trip
# ══════════════════════════════════════════════════════════════════════════════

class TestClassesPersistence(unittest.TestCase):

    def test_round_trip(self):
        """Classes and enrollments survive a save_dataset / load_dataset cycle."""
        from app.storage.sqlite_storage import SqliteStorage
        from app.services.class_manager import ClassManager
        from app.models.student import Student

        db_path = os.path.join(tempfile.gettempdir(), f"a6_test_{os.getpid()}.db")
        try:
            stor = SqliteStorage(db_path)

            student = Student(name="Test Student", grade=75.0)
            cm = ClassManager()
            cls = cm.add_class("PHY101", "Physics I", credits=3.0)
            cm.enroll(student.id, cls.id)

            ok = stor.save_dataset(
                students=[student],
                classes=cm.classes_to_list(),
                enrollments=cm.enrollments_to_list(),
            )
            self.assertTrue(ok)
            stor._conn.close()  # release the file lock before reloading

            # Load into fresh objects
            stor2 = SqliteStorage(db_path)
            payload = stor2.load_dataset()
            stor2._conn.close()

            self.assertEqual(len(payload.students), 1)
            self.assertEqual(payload.students[0].name, "Test Student")
            self.assertEqual(len(payload.classes), 1)
            self.assertEqual(payload.classes[0]["code"], "PHY101")
            self.assertEqual(len(payload.enrollments), 1)
            self.assertEqual(payload.enrollments[0]["student_id"], student.id)
            self.assertEqual(payload.enrollments[0]["class_id"], cls.id)
        finally:
            try:
                os.remove(db_path)
            except OSError:
                pass


if __name__ == "__main__":
    unittest.main()
