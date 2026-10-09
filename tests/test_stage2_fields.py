"""
Tests for Stage 2: linkedin_url, department, groups fields and group management.
Covers model, sqlite storage round-trip, and StudentManager helpers.
"""

import unittest

from app.models.student import Student, CourseGrade
from app.storage.sqlite_storage import SqliteStorage
from app.services.student_manager import StudentManager


def _mem_manager() -> StudentManager:
    return StudentManager(SqliteStorage(":memory:"))


# ---------------------------------------------------------------------------
# Model — new fields
# ---------------------------------------------------------------------------

class TestStudentNewFields(unittest.TestCase):

    def test_defaults_are_empty(self):
        s = Student("Alice", 80)
        self.assertEqual(s.linkedin_url, "")
        self.assertEqual(s.department, "")
        self.assertEqual(s.groups, [])

    def test_constructor_sets_fields(self):
        s = Student("Bob", 75, linkedin_url="https://linkedin.com/in/bob",
                    department="Engineering", groups=["A", "B"])
        self.assertEqual(s.linkedin_url, "https://linkedin.com/in/bob")
        self.assertEqual(s.department, "Engineering")
        self.assertEqual(s.groups, ["A", "B"])

    def test_setters(self):
        s = Student("Carol", 70)
        s.linkedin_url = "  https://linkedin.com/in/carol  "
        s.department = "  Arts  "
        s.groups = ["X"]
        self.assertEqual(s.linkedin_url, "https://linkedin.com/in/carol")
        self.assertEqual(s.department, "Arts")
        self.assertEqual(s.groups, ["X"])

    def test_to_dict_includes_new_fields(self):
        s = Student("Diana", 88, linkedin_url="https://li.com/d",
                    department="Science", groups=["Cohort1"])
        d = s.to_dict()
        self.assertEqual(d["linkedin_url"], "https://li.com/d")
        self.assertEqual(d["department"], "Science")
        self.assertEqual(d["groups"], ["Cohort1"])

    def test_from_dict_round_trip(self):
        s = Student("Eve", 65, linkedin_url="https://li.com/e",
                    department="Math", groups=["G1", "G2"])
        s2 = Student.from_dict(s.to_dict())
        self.assertEqual(s2.linkedin_url, "https://li.com/e")
        self.assertEqual(s2.department, "Math")
        self.assertEqual(s2.groups, ["G1", "G2"])

    def test_from_dict_backward_compat(self):
        """Legacy dicts without new fields must load cleanly."""
        legacy = {"id": "abc", "name": "Frank", "grade": 50.0,
                  "email": "", "major": "", "academic_year": "",
                  "gpa": None, "courses": [], "notes": ""}
        s = Student.from_dict(legacy)
        self.assertEqual(s.linkedin_url, "")
        self.assertEqual(s.department, "")
        self.assertEqual(s.groups, [])

    def test_groups_copy_on_read(self):
        """groups property returns a copy — external mutation is harmless."""
        s = Student("Grace", 90, groups=["A"])
        g = s.groups
        g.append("B")
        self.assertEqual(s.groups, ["A"])


# ---------------------------------------------------------------------------
# SqliteStorage — new fields round-trip
# ---------------------------------------------------------------------------

class TestSqliteStorageNewFields(unittest.TestCase):

    def setUp(self):
        self.store = SqliteStorage(":memory:")

    def test_new_fields_saved_and_loaded(self):
        s = Student("Henry", 72, linkedin_url="https://li.com/h",
                    department="CS", groups=["Team1", "Honors"])
        self.store.save([s])
        loaded = self.store.load()[0]
        self.assertEqual(loaded.linkedin_url, "https://li.com/h")
        self.assertEqual(loaded.department, "CS")
        self.assertIn("Team1", loaded.groups)
        self.assertIn("Honors", loaded.groups)

    def test_empty_groups_round_trip(self):
        s = Student("Isla", 60)
        self.store.save([s])
        loaded = self.store.load()[0]
        self.assertEqual(loaded.groups, [])
        self.assertEqual(loaded.linkedin_url, "")
        self.assertEqual(loaded.department, "")

    def test_multiple_groups_round_trip(self):
        s = Student("Jack", 85, groups=["A", "B", "C"])
        self.store.save([s])
        loaded = self.store.load()[0]
        self.assertEqual(sorted(loaded.groups), ["A", "B", "C"])


# ---------------------------------------------------------------------------
# StudentManager — group helpers
# ---------------------------------------------------------------------------

class TestStudentManagerGroups(unittest.TestCase):

    def setUp(self):
        self.mgr = _mem_manager()
        self.mgr.add_student("Alice", 90, department="CS", groups=["A"])
        self.mgr.add_student("Bob",   75, department="Math", groups=["A", "B"])
        self.mgr.add_student("Carol", 60, department="CS")

    def test_list_groups(self):
        groups = self.mgr.list_groups()
        self.assertIn("A", groups)
        self.assertIn("B", groups)
        self.assertEqual(groups, sorted(groups))

    def test_list_departments(self):
        depts = self.mgr.list_departments()
        self.assertIn("CS", depts)
        self.assertIn("Math", depts)
        self.assertEqual(depts, sorted(depts))

    def test_assign_group_adds_group(self):
        s = self.mgr.get_all_students()[2]  # Carol — no groups
        self.mgr.assign_group(s.id, "C")
        self.assertIn("C", s.groups)

    def test_assign_group_idempotent(self):
        s = self.mgr.get_all_students()[0]  # Alice — already in "A"
        self.mgr.assign_group(s.id, "A")
        self.assertEqual(s.groups.count("A"), 1)

    def test_assign_group_empty_name_raises(self):
        s = self.mgr.get_all_students()[0]
        with self.assertRaises(ValueError):
            self.mgr.assign_group(s.id, "  ")

    def test_assign_group_unknown_id_raises(self):
        with self.assertRaises(ValueError):
            self.mgr.assign_group("nonexistent-id", "X")

    def test_remove_from_group(self):
        s = self.mgr.get_all_students()[1]  # Bob — in A and B
        self.mgr.remove_from_group(s.id, "A")
        self.assertNotIn("A", s.groups)
        self.assertIn("B", s.groups)

    def test_remove_from_group_idempotent(self):
        s = self.mgr.get_all_students()[0]
        self.mgr.remove_from_group(s.id, "nonexistent-group")
        # Should not raise

    def test_filter_by_group(self):
        results = self.mgr.filter_by_group("A")
        names = {s.name for _, s in results}
        self.assertIn("Alice", names)
        self.assertIn("Bob", names)
        self.assertNotIn("Carol", names)

    def test_filter_by_department(self):
        results = self.mgr.filter_by_department("CS")
        names = {s.name for _, s in results}
        self.assertIn("Alice", names)
        self.assertIn("Carol", names)
        self.assertNotIn("Bob", names)

    def test_filter_by_department_case_insensitive(self):
        results = self.mgr.filter_by_department("cs")
        self.assertTrue(len(results) > 0)

    def test_add_student_with_new_fields(self):
        s = self.mgr.add_student("Dave", 80, linkedin_url="https://li.com/dave",
                                  department="Bio", groups=["G"])
        self.assertEqual(s.linkedin_url, "https://li.com/dave")
        self.assertEqual(s.department, "Bio")
        self.assertEqual(s.groups, ["G"])

    def test_update_student_new_fields(self):
        s = self.mgr.get_all_students()[0]
        self.mgr.update_student(s.id, linkedin_url="https://li.com/new",
                                 department="Physics", groups=["Z"])
        updated = self.mgr.get_by_id(s.id)
        self.assertEqual(updated.linkedin_url, "https://li.com/new")
        self.assertEqual(updated.department, "Physics")
        self.assertEqual(updated.groups, ["Z"])


# ---------------------------------------------------------------------------
# StudentManager — persistence with new fields
# ---------------------------------------------------------------------------

class TestStudentManagerPersistNewFields(unittest.TestCase):

    def test_save_and_reload_new_fields(self):
        mgr = _mem_manager()
        mgr.add_student("Eve", 70, linkedin_url="https://li.com/eve",
                         department="Art", groups=["Morning"])
        mgr.save()
        mgr.load()
        s = mgr.get_all_students()[0]
        self.assertEqual(s.linkedin_url, "https://li.com/eve")
        self.assertEqual(s.department, "Art")
        self.assertIn("Morning", s.groups)


if __name__ == "__main__":
    unittest.main()
