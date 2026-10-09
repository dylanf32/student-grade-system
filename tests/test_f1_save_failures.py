"""
F1 — Tests for truthful save failures.

Verifies that add/update/delete/sort return HTTP 503 with success=false when
saving fails, that state is rolled back to what it was before the mutation,
and that a successful save returns 200/success=true.
"""

import json
import sys
import os
import unittest
from unittest.mock import patch

# Ensure the project root is on the path when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run_web
from app.models.student import Student
from app.storage.base_storage import BaseStorage


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class FailingStorage(BaseStorage):
    """Storage that always fails to save but loads fine."""

    def __init__(self, initial: list[Student] | None = None):
        self._data = [s.to_dict() for s in (initial or [])]

    def save(self, students):
        return False  # always fails

    def load(self):
        return [Student.from_dict(d) for d in self._data]


class SucceedingStorage(BaseStorage):
    """In-memory storage that always succeeds."""

    def __init__(self, initial: list[Student] | None = None):
        self._data = [s.to_dict() for s in (initial or [])]

    def save(self, students):
        self._data = [s.to_dict() for s in students]
        return True

    def load(self):
        return [Student.from_dict(d) for d in self._data]


def _make_client(storage):
    """Return a Flask test client backed by the given storage."""
    from app.services.student_manager import StudentManager
    mgr = StudentManager(storage)
    mgr.load()
    run_web.manager = mgr
    run_web.app.config["TESTING"] = True
    return run_web.app.test_client()


# ---------------------------------------------------------------------------
# Add — failed save
# ---------------------------------------------------------------------------

class TestAddSaveFailure(unittest.TestCase):

    def setUp(self):
        self.storage = FailingStorage()
        self.client = _make_client(self.storage)

    def test_add_returns_503_on_save_failure(self):
        resp = self.client.post(
            "/api/students",
            json={"name": "Test Student", "grade": 75},
        )
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_add_rolls_back_on_save_failure(self):
        """After a failed save, the student must not remain in memory."""
        self.client.post("/api/students", json={"name": "Ghost", "grade": 80})
        resp = self.client.get("/api/students")
        students = resp.get_json()
        names = [s["name"] for s in students]
        self.assertNotIn("Ghost", names)


# ---------------------------------------------------------------------------
# Update — failed save
# ---------------------------------------------------------------------------

class TestUpdateSaveFailure(unittest.TestCase):

    def setUp(self):
        # Pre-seed one student via succeeding storage, then swap to failing.
        seed_storage = SucceedingStorage()
        seed_mgr_client = _make_client(seed_storage)
        resp = seed_mgr_client.post(
            "/api/students", json={"name": "Original", "grade": 70}
        )
        self.student_id = resp.get_json()["student"]["student_id"]
        # Swap to failing storage with the same data.
        self.storage = FailingStorage(initial=seed_storage.load())
        self.client = _make_client(self.storage)

    def test_update_returns_503_on_save_failure(self):
        resp = self.client.put(
            f"/api/students/{self.student_id}",
            json={"grade": 99},
        )
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertFalse(data["success"])

    def test_update_rolls_back_on_save_failure(self):
        """Grade must be restored to its pre-update value after a failed save."""
        self.client.put(f"/api/students/{self.student_id}", json={"grade": 99})
        resp = self.client.get("/api/students")
        students = resp.get_json()
        student = next(s for s in students if s["student_id"] == self.student_id)
        self.assertEqual(student["grade"], 70)


# ---------------------------------------------------------------------------
# Delete — failed save
# ---------------------------------------------------------------------------

class TestDeleteSaveFailure(unittest.TestCase):

    def setUp(self):
        seed_storage = SucceedingStorage()
        seed_client = _make_client(seed_storage)
        resp = seed_client.post(
            "/api/students", json={"name": "ToDelete", "grade": 65}
        )
        self.student_id = resp.get_json()["student"]["student_id"]
        self.storage = FailingStorage(initial=seed_storage.load())
        self.client = _make_client(self.storage)

    def test_delete_returns_503_on_save_failure(self):
        resp = self.client.delete(f"/api/students/{self.student_id}")
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertFalse(data["success"])

    def test_delete_rolls_back_on_save_failure(self):
        """Student must still exist in memory after a failed delete-save."""
        self.client.delete(f"/api/students/{self.student_id}")
        resp = self.client.get("/api/students")
        students = resp.get_json()
        ids = [s["student_id"] for s in students]
        self.assertIn(self.student_id, ids)


# ---------------------------------------------------------------------------
# Sort — failed save
# ---------------------------------------------------------------------------

class TestSortSaveFailure(unittest.TestCase):

    def setUp(self):
        self.storage = FailingStorage()
        self.client = _make_client(self.storage)

    def test_sort_returns_503_on_save_failure(self):
        resp = self.client.get("/api/sort?ascending=true")
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertFalse(data["success"])
        # Sorted list still returned for best-effort display
        self.assertIn("students", data)


# ---------------------------------------------------------------------------
# /api/save — failed and successful
# ---------------------------------------------------------------------------

class TestExplicitSave(unittest.TestCase):

    def test_save_returns_503_on_failure(self):
        storage = FailingStorage()
        client = _make_client(storage)
        resp = client.post("/api/save")
        self.assertEqual(resp.status_code, 503)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_save_returns_200_on_success(self):
        storage = SucceedingStorage()
        client = _make_client(storage)
        resp = client.post("/api/save")
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])


# ---------------------------------------------------------------------------
# Successful CRUD — sanity check
# ---------------------------------------------------------------------------

class TestSuccessfulCRUD(unittest.TestCase):
    """Verify that working storage still gives success=true responses."""

    def setUp(self):
        self.storage = SucceedingStorage()
        self.client = _make_client(self.storage)

    def test_add_succeeds(self):
        resp = self.client.post(
            "/api/students", json={"name": "Alice", "grade": 88}
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.student_id = data["student"]["student_id"]

    def test_add_then_delete_succeeds(self):
        resp = self.client.post(
            "/api/students", json={"name": "Bob", "grade": 72}
        )
        sid = resp.get_json()["student"]["student_id"]
        del_resp = self.client.delete(f"/api/students/{sid}")
        self.assertEqual(del_resp.status_code, 200)
        self.assertTrue(del_resp.get_json()["success"])

    def test_add_then_update_succeeds(self):
        resp = self.client.post(
            "/api/students", json={"name": "Carol", "grade": 60}
        )
        sid = resp.get_json()["student"]["student_id"]
        upd_resp = self.client.put(f"/api/students/{sid}", json={"grade": 85})
        self.assertEqual(upd_resp.status_code, 200)
        self.assertTrue(upd_resp.get_json()["success"])


if __name__ == "__main__":
    unittest.main()
