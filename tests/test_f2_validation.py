"""
F2 — Tests for input validation before record changes.

Covers the reported cases (boolean grades/GPA, non-string fields, bad courses),
invalid-later-update-fields, and a valid decimal/course round trip.
"""

import sys
import os
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import run_web
from app.services.student_manager import StudentManager
from app.storage.base_storage import BaseStorage
from app.models.student import Student
from app.validators.input_validator import InputValidator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class MemStorage(BaseStorage):
    def __init__(self):
        self._data = []

    def save(self, students):
        self._data = [s.to_dict() for s in students]
        return True

    def load(self):
        return [Student.from_dict(d) for d in self._data]


def _client():
    mgr = StudentManager(MemStorage())
    mgr.load()
    run_web.manager = mgr
    run_web.app.config["TESTING"] = True
    return run_web.app.test_client()


def _add_student(client, **kwargs):
    """POST a student with default valid fields plus overrides."""
    payload = {"name": "Test User", "grade": 75, **kwargs}
    return client.post("/api/students", json=payload)


# ---------------------------------------------------------------------------
# InputValidator unit tests
# ---------------------------------------------------------------------------

class TestValidateGpa(unittest.TestCase):

    def test_none_is_valid(self):
        ok, _ = InputValidator.validate_gpa(None)
        self.assertTrue(ok)

    def test_valid_float(self):
        ok, _ = InputValidator.validate_gpa(3.5)
        self.assertTrue(ok)

    def test_valid_int(self):
        ok, _ = InputValidator.validate_gpa(4)
        self.assertTrue(ok)

    def test_valid_string(self):
        ok, _ = InputValidator.validate_gpa("3.5")
        self.assertTrue(ok)

    def test_boolean_true_rejected(self):
        ok, msg = InputValidator.validate_gpa(True)
        self.assertFalse(ok)
        self.assertIn("number", msg)

    def test_boolean_false_rejected(self):
        ok, msg = InputValidator.validate_gpa(False)
        self.assertFalse(ok)

    def test_above_4_rejected(self):
        ok, msg = InputValidator.validate_gpa(8)
        self.assertFalse(ok)
        self.assertIn("4.0", msg)

    def test_negative_rejected(self):
        ok, _ = InputValidator.validate_gpa(-0.1)
        self.assertFalse(ok)

    def test_boundary_zero(self):
        ok, _ = InputValidator.validate_gpa(0.0)
        self.assertTrue(ok)

    def test_boundary_four(self):
        ok, _ = InputValidator.validate_gpa(4.0)
        self.assertTrue(ok)


class TestValidateCourseGrade(unittest.TestCase):

    def test_none_is_valid(self):
        ok, _ = InputValidator.validate_course_grade(None)
        self.assertTrue(ok)

    def test_zero_is_valid(self):
        ok, _ = InputValidator.validate_course_grade(0)
        self.assertTrue(ok)

    def test_hundred_is_valid(self):
        ok, _ = InputValidator.validate_course_grade(100)
        self.assertTrue(ok)

    def test_decimal_is_valid(self):
        ok, _ = InputValidator.validate_course_grade(87.5)
        self.assertTrue(ok)

    def test_string_numeric_is_valid(self):
        ok, _ = InputValidator.validate_course_grade("85.0")
        self.assertTrue(ok)

    def test_boolean_true_rejected(self):
        ok, msg = InputValidator.validate_course_grade(True)
        self.assertFalse(ok)

    def test_boolean_false_rejected(self):
        ok, msg = InputValidator.validate_course_grade(False)
        self.assertFalse(ok)

    def test_above_100_rejected(self):
        ok, msg = InputValidator.validate_course_grade(101)
        self.assertFalse(ok)

    def test_negative_rejected(self):
        ok, _ = InputValidator.validate_course_grade(-1)
        self.assertFalse(ok)


# ---------------------------------------------------------------------------
# POST /api/students — boolean grade/GPA
# ---------------------------------------------------------------------------

class TestAddBooleanRejected(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_boolean_grade_true_rejected(self):
        resp = _add_student(self.client, grade=True)
        self.assertEqual(resp.status_code, 400)
        self.assertFalse(resp.get_json()["success"])

    def test_boolean_grade_false_rejected(self):
        resp = _add_student(self.client, grade=False)
        self.assertEqual(resp.status_code, 400)

    def test_boolean_gpa_true_rejected(self):
        resp = _add_student(self.client, gpa=True)
        self.assertEqual(resp.status_code, 400)

    def test_gpa_above_4_rejected(self):
        resp = _add_student(self.client, gpa=8)
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data["success"])
        self.assertIn("error", data)

    def test_non_string_name_rejected(self):
        resp = _add_student(self.client, name=123)
        self.assertEqual(resp.status_code, 400)

    def test_non_string_email_rejected(self):
        resp = _add_student(self.client, email=True)
        self.assertEqual(resp.status_code, 400)

    def test_non_dict_body_rejected(self):
        resp = self.client.post(
            "/api/students",
            data="[1,2,3]",
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 400)

    def test_state_unchanged_after_bad_gpa(self):
        """No student should be added when GPA is invalid."""
        before = self.client.get("/api/students").get_json()
        _add_student(self.client, gpa=8)
        after = self.client.get("/api/students").get_json()
        self.assertEqual(len(before), len(after))


# ---------------------------------------------------------------------------
# POST — course validation
# ---------------------------------------------------------------------------

class TestAddCourseValidation(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_boolean_course_grade_rejected(self):
        resp = _add_student(
            self.client,
            courses=[{"course": "Math", "grade": True}],
        )
        self.assertEqual(resp.status_code, 400)

    def test_empty_course_name_rejected(self):
        resp = _add_student(
            self.client,
            courses=[{"course": "", "grade": 80}],
        )
        self.assertEqual(resp.status_code, 400)

    def test_non_string_course_name_rejected(self):
        resp = _add_student(
            self.client,
            courses=[{"course": 123, "grade": 80}],
        )
        self.assertEqual(resp.status_code, 400)

    def test_course_grade_above_100_rejected(self):
        resp = _add_student(
            self.client,
            courses=[{"course": "Math", "grade": 110}],
        )
        self.assertEqual(resp.status_code, 400)

    def test_null_course_grade_accepted(self):
        resp = _add_student(
            self.client,
            courses=[{"course": "Math", "grade": None}],
        )
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.get_json()["success"])

    def test_courses_not_a_list_rejected(self):
        resp = _add_student(self.client, courses={"course": "Math"})
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# PUT /api/students/<id> — validate before applying
# ---------------------------------------------------------------------------

class TestUpdateValidation(unittest.TestCase):

    def setUp(self):
        self.client = _client()
        resp = _add_student(self.client, grade=70, gpa=2.5)
        self.sid = resp.get_json()["student"]["student_id"]

    def test_boolean_grade_rejected(self):
        resp = self.client.put(f"/api/students/{self.sid}", json={"grade": True})
        self.assertEqual(resp.status_code, 400)

    def test_gpa_above_4_rejected(self):
        resp = self.client.put(f"/api/students/{self.sid}", json={"gpa": 8})
        self.assertEqual(resp.status_code, 400)

    def test_non_string_field_rejected(self):
        resp = self.client.put(f"/api/students/{self.sid}", json={"email": 999})
        self.assertEqual(resp.status_code, 400)

    def test_invalid_later_field_prevents_all_changes(self):
        """A valid grade + invalid GPA must leave the record unchanged."""
        resp = self.client.put(
            f"/api/students/{self.sid}",
            json={"grade": 90, "gpa": 8},
        )
        self.assertEqual(resp.status_code, 400)
        # Grade must still be 70 (not 90)
        students = self.client.get("/api/students").get_json()
        s = next(x for x in students if x["student_id"] == self.sid)
        self.assertEqual(s["grade"], 70)

    def test_boolean_course_grade_in_update_rejected(self):
        resp = self.client.put(
            f"/api/students/{self.sid}",
            json={"courses": [{"course": "Math", "grade": True}]},
        )
        self.assertEqual(resp.status_code, 400)


# ---------------------------------------------------------------------------
# Valid decimal / course round trip
# ---------------------------------------------------------------------------

class TestValidRoundTrip(unittest.TestCase):

    def setUp(self):
        self.client = _client()

    def test_decimal_grade_and_course(self):
        resp = _add_student(
            self.client,
            name="Decimal Test",
            grade=87.5,
            gpa=3.75,
            courses=[{"course": "Physics", "grade": 92.5}],
        )
        self.assertEqual(resp.status_code, 200)
        payload = resp.get_json()["student"]
        self.assertEqual(payload["grade"], 87.5)
        self.assertEqual(payload["courses"][0]["grade"], 92.5)

    def test_numeric_string_grade_accepted(self):
        """grade supplied as a string should be coerced to float."""
        resp = _add_student(self.client, name="String Grade", grade="77")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.get_json()["student"]["grade"], 77.0)

    def test_415_preserved_for_wrong_content_type(self):
        resp = self.client.post(
            "/api/students",
            data="name=Test&grade=80",
            content_type="application/x-www-form-urlencoded",
        )
        self.assertEqual(resp.status_code, 415)


if __name__ == "__main__":
    unittest.main()
