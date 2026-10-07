"""
Unit tests for the Student model.
"""

import unittest

from app.models.student import Student


class TestStudentCreation(unittest.TestCase):
    """Tests for Student construction and validation."""

    def test_valid_student(self):
        s = Student("Ali", 85)
        self.assertEqual(s.name, "Ali")
        self.assertEqual(s.grade, 85)

    def test_boundary_grade_zero(self):
        s = Student("Ahmed", 0)
        self.assertEqual(s.grade, 0)

    def test_boundary_grade_hundred(self):
        s = Student("Sara", 100)
        self.assertEqual(s.grade, 100)

    def test_name_stripped(self):
        s = Student("  Fatima  ", 70)
        self.assertEqual(s.name, "Fatima")

    def test_empty_name_raises(self):
        with self.assertRaises(ValueError):
            Student("", 50)

    def test_whitespace_name_raises(self):
        with self.assertRaises(ValueError):
            Student("   ", 50)

    def test_negative_grade_raises(self):
        with self.assertRaises(ValueError):
            Student("Ali", -1)

    def test_grade_over_100_raises(self):
        with self.assertRaises(ValueError):
            Student("Ali", 101)


class TestStudentGradeSetter(unittest.TestCase):
    """Tests for the grade property setter."""

    def setUp(self):
        self.student = Student("Test", 50)

    def test_set_valid_grade(self):
        self.student.grade = 95
        self.assertEqual(self.student.grade, 95)

    def test_set_invalid_grade_raises(self):
        with self.assertRaises(ValueError):
            self.student.grade = -5
        with self.assertRaises(ValueError):
            self.student.grade = 110


class TestStudentSerialization(unittest.TestCase):
    """Tests for to_dict / from_dict."""

    def test_to_dict(self):
        s = Student("Zain", 88)
        d = s.to_dict()
        self.assertEqual(d["name"], "Zain")
        self.assertEqual(d["grade"], 88)
        self.assertIn("id", d)  # UUID must now be present

    def test_from_dict(self):
        s = Student.from_dict({"name": "Hira", "grade": 92})
        self.assertEqual(s.name, "Hira")
        self.assertEqual(s.grade, 92)

    def test_roundtrip(self):
        original = Student("Ali", 77)
        rebuilt  = Student.from_dict(original.to_dict())
        self.assertEqual(original, rebuilt)

    def test_str(self):
        s = Student("Ali", 80)
        self.assertIn("Ali", str(s))
        self.assertIn("80", str(s))

    def test_repr(self):
        s = Student("Ali", 80)
        r = repr(s)
        self.assertIn("Ali", r)
        self.assertIn("80", r)
        self.assertIn(s.id, r)


class TestStudentFromDictMalformed(unittest.TestCase):
    """Tests for from_dict() with missing or invalid input."""

    def test_missing_name_raises(self):
        with self.assertRaises(ValueError):
            Student.from_dict({"grade": 50})

    def test_missing_grade_raises(self):
        with self.assertRaises(ValueError):
            Student.from_dict({"name": "Ali"})

    def test_none_input_raises(self):
        with self.assertRaises(ValueError):
            Student.from_dict(None)


class TestStudentEquality(unittest.TestCase):
    """Tests for __eq__.

    Students are equal iff they share the same UUID.  Two independently
    created students with identical name/grade are distinct entities.
    """

    def test_equal_students_same_uuid(self):
        """A student round-tripped through to_dict/from_dict must be equal."""
        a = Student("Ali", 80)
        b = Student.from_dict(a.to_dict())
        self.assertEqual(a, b)

    def test_different_uuid_not_equal(self):
        """Two freshly created students with the same name/grade differ."""
        a = Student("Ali", 80)
        b = Student("Ali", 80)
        self.assertNotEqual(a, b)

    def test_different_students(self):
        a = Student("Ali", 80)
        b = Student("Ali", 90)
        self.assertNotEqual(a, b)


# ── UUID / stable identity tests ─────────────────────────────────────────────

class TestStudentUUID(unittest.TestCase):
    """Students must carry stable, unique IDs."""

    def test_new_student_gets_uuid(self):
        s = Student("Ali", 85)
        self.assertIsNotNone(s.id)
        self.assertGreater(len(s.id), 0)

    def test_two_students_have_different_ids(self):
        a = Student("Ali", 85)
        b = Student("Ali", 85)
        self.assertNotEqual(a.id, b.id)

    def test_id_preserved_through_serialisation(self):
        """Round-trip through to_dict/from_dict must keep the same UUID."""
        original = Student("Sara", 90)
        rebuilt = Student.from_dict(original.to_dict())
        self.assertEqual(original.id, rebuilt.id)

    def test_from_dict_without_id_generates_uuid(self):
        """Legacy JSON records without an id key must be assigned a UUID."""
        legacy = {"name": "Old Student", "grade": 70}
        s = Student.from_dict(legacy)
        self.assertIsNotNone(s.id)
        self.assertGreater(len(s.id), 0)

    def test_deleting_one_student_does_not_change_other_ids(self):
        """IDs of remaining students must be unaffected by a deletion."""
        from app.services.student_manager import StudentManager
        from app.storage.base_storage import BaseStorage

        class FakeStorage(BaseStorage):
            def save(self, students):
                return True
            def load(self):
                return []

        mgr = StudentManager(FakeStorage())
        mgr.add_student("Alice", 85)
        mgr.add_student("Bob", 70)
        mgr.add_student("Carol", 90)

        ids_before = [s.id for s in mgr.get_all_students()]
        # Delete the first student (index 0).
        mgr.remove_student(0)
        ids_after = [s.id for s in mgr.get_all_students()]

        # Bob and Carol's UUIDs must be unchanged.
        self.assertEqual(ids_before[1], ids_after[0])
        self.assertEqual(ids_before[2], ids_after[1])

    def test_stale_id_does_not_match_any_remaining_student(self):
        """An already-deleted UUID must not match any surviving student."""
        from app.services.student_manager import StudentManager
        from app.storage.base_storage import BaseStorage

        class FakeStorage(BaseStorage):
            def save(self, students):
                return True
            def load(self):
                return []

        mgr = StudentManager(FakeStorage())
        mgr.add_student("Alice", 85)
        mgr.add_student("Bob", 70)

        students = mgr.get_all_students()
        stale_id = students[0].id
        mgr.remove_student(0)

        remaining_ids = [s.id for s in mgr.get_all_students()]
        self.assertNotIn(stale_id, remaining_ids)


if __name__ == "__main__":
    unittest.main()
