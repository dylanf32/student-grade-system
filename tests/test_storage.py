"""
Unit tests for JSON storage backend.
"""

import json
import os
import tempfile
import unittest
from unittest.mock import patch

from app.models.student import Student
from app.storage.json_storage import JsonStorage


class TestJsonStorage(unittest.TestCase):
    """Tests for JsonStorage save/load."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.tmp.close()
        self.storage = JsonStorage(file_path=self.tmp.name)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_save_creates_file(self):
        os.unlink(self.tmp.name)  # start clean
        students = [Student("Ali", 85)]
        self.storage.save(students)
        self.assertTrue(os.path.exists(self.tmp.name))

    def test_save_and_load_roundtrip(self):
        students = [Student("Ali", 85), Student("Sara", 90)]
        self.storage.save(students)

        loaded = self.storage.load()
        self.assertEqual(len(loaded), 2)
        self.assertEqual(loaded[0].name, "Ali")
        self.assertEqual(loaded[1].grade, 90)

    def test_load_nonexistent_file(self):
        storage = JsonStorage(file_path="nonexistent_xyz.json")
        result = storage.load()
        self.assertEqual(result, [])

    def test_load_corrupted_file(self):
        with open(self.tmp.name, "w") as f:
            f.write("NOT VALID JSON{{{")
        result = self.storage.load()
        self.assertEqual(result, [])

    def test_save_empty_list(self):
        self.storage.save([])
        loaded = self.storage.load()
        self.assertEqual(loaded, [])

    def test_json_structure(self):
        """Saved JSON must contain id, name, and grade keys."""
        students = [Student("Ali", 85)]
        self.storage.save(students)

        with open(self.tmp.name, "r") as f:
            data = json.load(f)

        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["name"], "Ali")
        self.assertEqual(data[0]["grade"], 85)
        self.assertIn("id", data[0])  # UUID must be persisted


# ── Atomic-save tests ────────────────────────────────────────────────────────

class TestAtomicSave(unittest.TestCase):
    """Verify that the original file is never corrupted on save failure."""

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        self.tmp.close()
        self.storage = JsonStorage(file_path=self.tmp.name)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_normal_save_works(self):
        """A successful save persists all students correctly."""
        students = [Student("Ahmed", 75), Student("Noor", 80)]
        result = self.storage.save(students)
        self.assertTrue(result)
        loaded = self.storage.load()
        self.assertEqual(len(loaded), 2)

    def test_original_preserved_when_serialisation_fails(self):
        """If json.dump raises, the original file must be untouched."""
        # Seed the file with known valid data.
        good_students = [Student("Safe", 70)]
        self.storage.save(good_students)

        # Patch json.dump to blow up mid-write.
        with patch("json.dump", side_effect=ValueError("simulated failure")):
            result = self.storage.save([Student("New", 55)])

        self.assertFalse(result)

        # The original data must still be intact.
        loaded = self.storage.load()
        self.assertEqual(len(loaded), 1)
        self.assertEqual(loaded[0].name, "Safe")

    def test_no_tmp_file_left_after_failure(self):
        """Temp files must be cleaned up after a write failure."""
        target_dir = os.path.dirname(self.tmp.name)

        # Count .tmp files before.
        before = set(
            f for f in os.listdir(target_dir) if f.endswith(".tmp")
        )

        with patch("json.dump", side_effect=IOError("disk full")):
            self.storage.save([Student("X", 50)])

        after = set(
            f for f in os.listdir(target_dir) if f.endswith(".tmp")
        )
        # No new temp files should remain.
        self.assertEqual(before, after)

    def test_save_does_not_truncate_on_failure(self):
        """The original file must not be empty after a failed save."""
        good_students = [Student("Keeper", 88)]
        self.storage.save(good_students)

        with patch("json.dump", side_effect=RuntimeError("boom")):
            self.storage.save([Student("Ghost", 10)])

        self.assertGreater(os.path.getsize(self.tmp.name), 0)


if __name__ == "__main__":
    unittest.main()
