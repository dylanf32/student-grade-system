"""
Unit tests for SQLite storage backend.
"""

import json
import unittest

from app.models.student import Student, CourseGrade
from app.storage.sqlite_storage import SqliteStorage


def _mem() -> SqliteStorage:
    """Return an in-memory SqliteStorage instance."""
    return SqliteStorage(":memory:")


class TestSqliteStorageSchema(unittest.TestCase):
    """Schema initialisation tests."""

    def test_init_does_not_raise(self):
        """Creating an in-memory store must not raise."""
        store = _mem()
        self.assertIsNotNone(store)

    def test_load_empty_on_fresh_db(self):
        """A freshly created database returns an empty list."""
        self.assertEqual(_mem().load(), [])


class TestSqliteStorageSaveLoad(unittest.TestCase):
    """Round-trip save/load tests."""

    def setUp(self):
        self.store = _mem()

    def test_save_and_load_single(self):
        students = [Student("Alice", 85)]
        self.store.save(students)
        loaded = self.store.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].name, "Alice")
        self.assertEqual(loaded[0].grade, 85.0)

    def test_save_and_load_multiple(self):
        students = [Student("Alice", 85), Student("Bob", 72)]
        self.store.save(students)
        loaded = self.store.load()
        self.assertEqual(len(loaded), 2)
        names = {s.name for s in loaded}
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)

    def test_save_empty_list(self):
        self.store.save([Student("Alice", 85)])
        self.store.save([])
        self.assertEqual(self.store.load(), [])

    def test_uuid_preserved(self):
        s = Student("Charlie", 90)
        original_id = s.id
        self.store.save([s])
        loaded = self.store.load()
        self.assertEqual(loaded[0].id, original_id)

    def test_all_fields_preserved(self):
        s = Student(
            name="Diana",
            grade=78.5,
            email="diana@example.com",
            major="Engineering",
            academic_year="Sophomore",
            gpa=3.2,
            courses=[CourseGrade("Math 101", 82.0)],
            notes="Dean's list candidate",
        )
        self.store.save([s])
        loaded = self.store.load()[0]

        self.assertEqual(loaded.name, "Diana")
        self.assertAlmostEqual(loaded.grade, 78.5)
        self.assertEqual(loaded.email, "diana@example.com")
        self.assertEqual(loaded.major, "Engineering")
        self.assertEqual(loaded.academic_year, "Sophomore")
        self.assertAlmostEqual(loaded.gpa, 3.2)
        self.assertEqual(len(loaded.courses), 1)
        self.assertEqual(loaded.courses[0].course, "Math 101")
        self.assertAlmostEqual(loaded.courses[0].grade, 82.0)
        self.assertEqual(loaded.notes, "Dean's list candidate")

    def test_null_gpa_preserved(self):
        s = Student("Eve", 60, gpa=None)
        self.store.save([s])
        loaded = self.store.load()[0]
        self.assertIsNone(loaded.gpa)

    def test_empty_courses_preserved(self):
        s = Student("Frank", 55, courses=[])
        self.store.save([s])
        loaded = self.store.load()[0]
        self.assertEqual(loaded.courses, [])

    def test_multiple_courses_preserved(self):
        courses = [CourseGrade("CS 101", 95.0), CourseGrade("Math 202", 70.0)]
        s = Student("Grace", 82, courses=courses)
        self.store.save([s])
        loaded = self.store.load()[0]
        self.assertEqual(len(loaded.courses), 2)
        course_names = {c.course for c in loaded.courses}
        self.assertEqual(course_names, {"CS 101", "Math 202"})

    def test_save_replaces_previous_data(self):
        """Each save is a full replacement — no stale rows remain."""
        self.store.save([Student("Old", 50)])
        self.store.save([Student("New", 99)])
        loaded = self.store.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].name, "New")

    def test_second_save_does_not_duplicate(self):
        s = Student("Henry", 65)
        self.store.save([s])
        self.store.save([s])
        self.assertEqual(len(self.store.load()), 1)


class TestSqliteStorageMigration(unittest.TestCase):
    """Verify that JSON-sourced data survives the migration round-trip."""

    def test_json_data_migrates_intact(self):
        """Students loaded from JSON must serialize correctly to SQLite."""
        from app.storage.json_storage import JsonStorage
        import tempfile, os

        # Write a minimal JSON file mimicking the real data shape.
        sample = [
            {
                "id": "aaa-111",
                "name": "affan",
                "grade": 92.0,
                "email": "",
                "major": "",
                "academic_year": "",
                "gpa": None,
                "courses": [],
                "notes": "",
            }
        ]
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as fh:
            json.dump(sample, fh)
            tmp_path = fh.name

        try:
            json_store = JsonStorage(tmp_path)
            students = json_store.load()

            sqlite_store = _mem()
            ok = sqlite_store.save(students)
            self.assertTrue(ok)

            loaded = sqlite_store.load()
            self.assertEqual(len(loaded), 1)
            self.assertEqual(loaded[0].name, "affan")
            self.assertAlmostEqual(loaded[0].grade, 92.0)
            self.assertEqual(loaded[0].id, "aaa-111")
        finally:
            os.unlink(tmp_path)


if __name__ == "__main__":
    unittest.main()
