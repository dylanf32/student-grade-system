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
        self.assertEqual(s.to_dict(), {"name": "Zain", "grade": 88})

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


class TestStudentEquality(unittest.TestCase):
    """Tests for __eq__."""

    def test_equal_students(self):
        a = Student("Ali", 80)
        b = Student("Ali", 80)
        self.assertEqual(a, b)

    def test_different_students(self):
        a = Student("Ali", 80)
        b = Student("Ali", 90)
        self.assertNotEqual(a, b)


if __name__ == "__main__":
    unittest.main()
