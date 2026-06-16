"""
Unit tests for the StudentManager service.
"""

import unittest

from app.models.student import Student
from app.services.student_manager import StudentManager
from app.storage.base_storage import BaseStorage


class FakeStorage(BaseStorage):
    """In-memory fake storage for testing (no disk I/O)."""

    def __init__(self):
        self._data = []

    def save(self, students):
        self._data = [s.to_dict() for s in students]
        return True

    def load(self):
        return [Student.from_dict(d) for d in self._data]


class TestAddStudent(unittest.TestCase):
    """Tests for adding students."""

    def setUp(self):
        self.mgr = StudentManager(FakeStorage())

    def test_add_valid(self):
        s = self.mgr.add_student("Ali", 85)
        self.assertEqual(s.name, "Ali")
        self.assertEqual(self.mgr.size(), 1)

    def test_add_invalid_name(self):
        with self.assertRaises(ValueError):
            self.mgr.add_student("", 85)
        self.assertEqual(self.mgr.size(), 0)

    def test_add_invalid_grade(self):
        with self.assertRaises(ValueError):
            self.mgr.add_student("Ali", 150)
        self.assertEqual(self.mgr.size(), 0)

    def test_add_multiple(self):
        self.mgr.add_student("Ali", 85)
        self.mgr.add_student("Sara", 90)
        self.mgr.add_student("Ahmed", 75)
        self.assertEqual(self.mgr.size(), 3)


class TestRemoveStudent(unittest.TestCase):
    """Tests for removing students."""

    def setUp(self):
        self.mgr = StudentManager(FakeStorage())
        self.mgr.add_student("Ali", 85)
        self.mgr.add_student("Sara", 90)

    def test_remove_valid(self):
        removed = self.mgr.remove_student(0)
        self.assertEqual(removed.name, "Ali")
        self.assertEqual(self.mgr.size(), 1)

    def test_remove_invalid_index(self):
        with self.assertRaises(ValueError):
            self.mgr.remove_student(10)

    def test_remove_negative_index(self):
        with self.assertRaises(ValueError):
            self.mgr.remove_student(-1)


class TestUpdateGrade(unittest.TestCase):
    """Tests for updating grades."""

    def setUp(self):
        self.mgr = StudentManager(FakeStorage())
        self.mgr.add_student("Ali", 85)

    def test_update_valid(self):
        updated = self.mgr.update_grade(0, 95)
        self.assertEqual(updated.grade, 95)

    def test_update_invalid_index(self):
        with self.assertRaises(ValueError):
            self.mgr.update_grade(5, 90)

    def test_update_invalid_grade(self):
        with self.assertRaises(ValueError):
            self.mgr.update_grade(0, 200)


class TestSearchStudent(unittest.TestCase):
    """Tests for searching by name."""

    def setUp(self):
        self.mgr = StudentManager(FakeStorage())
        self.mgr.add_student("Ali", 85)
        self.mgr.add_student("Sara", 90)

    def test_search_found(self):
        self.assertEqual(self.mgr.search_by_name("Sara"), 1)

    def test_search_not_found(self):
        self.assertEqual(self.mgr.search_by_name("Zain"), -1)

    def test_search_case_insensitive(self):
        self.assertEqual(self.mgr.search_by_name("aLi"), 0)


class TestSortStudents(unittest.TestCase):
    """Tests for sorting."""

    def setUp(self):
        self.mgr = StudentManager(FakeStorage())
        self.mgr.add_student("Ali", 85)
        self.mgr.add_student("Sara", 60)
        self.mgr.add_student("Ahmed", 95)

    def test_sort_ascending(self):
        self.mgr.sort_by_grade(ascending=True)
        grades = [s.grade for s in self.mgr.get_all_students()]
        self.assertEqual(grades, [60, 85, 95])

    def test_sort_descending(self):
        self.mgr.sort_by_grade(ascending=False)
        grades = [s.grade for s in self.mgr.get_all_students()]
        self.assertEqual(grades, [95, 85, 60])


class TestPersistence(unittest.TestCase):
    """Tests for save / load via FakeStorage."""

    def test_save_and_load(self):
        storage = FakeStorage()
        mgr1 = StudentManager(storage)
        mgr1.add_student("Ali", 85)
        mgr1.add_student("Sara", 90)
        mgr1.save()

        mgr2 = StudentManager(storage)
        count = mgr2.load()
        self.assertEqual(count, 2)
        self.assertEqual(mgr2.get_student(0).name, "Ali")


if __name__ == "__main__":
    unittest.main()
