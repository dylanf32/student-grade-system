"""
Unit tests for JSON storage backend.
"""

import json
import os
import tempfile
import unittest

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
        students = [Student("Ali", 85)]
        self.storage.save(students)

        with open(self.tmp.name, "r") as f:
            data = json.load(f)

        self.assertIsInstance(data, list)
        self.assertEqual(data[0]["name"], "Ali")
        self.assertEqual(data[0]["grade"], 85)


if __name__ == "__main__":
    unittest.main()
