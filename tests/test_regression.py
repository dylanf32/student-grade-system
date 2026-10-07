"""
Regression tests covering all four issue areas:

1. Decimal grade input and storage  (Issue 1)
2. Grade status threshold boundaries (Issue 2)
3. Bare-filename storage             (Issue 3)
4. Duplicate student names & search  (Issue 4)
"""

import math
import os
import tempfile
import unittest

from app.config import (
    GRADE_EXCELLENT,
    GRADE_GOOD,
    GRADE_AVERAGE,
    GRADE_BELOW_AVG,
)
from app.models.student import Student
from app.services.statistics_service import StatisticsService
from app.services.student_manager import StudentManager
from app.storage.base_storage import BaseStorage
from app.storage.json_storage import JsonStorage
from app.validators.input_validator import InputValidator


# ── Shared fake storage ──────────────────────────────────────────────────────

class FakeStorage(BaseStorage):
    def save(self, students):
        return True
    def load(self):
        return []


# ═════════════════════════════════════════════════════════════════════════════
#  Issue 1 — Decimal grade input and storage
# ═════════════════════════════════════════════════════════════════════════════

class TestDecimalGradeRoundTrip(unittest.TestCase):
    """Decimal grades must survive construction, storage, and reload."""

    def _tmp_storage(self):
        fd, path = tempfile.mkstemp(suffix=".json")
        os.close(fd)
        os.unlink(path)            # start empty
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        return JsonStorage(file_path=path)

    def test_student_stores_decimal_grade(self):
        s = Student("Ana", 85.5)
        self.assertEqual(s.grade, 85.5)

    def test_decimal_grade_not_truncated(self):
        s = Student("Ana", 89.9)
        self.assertNotEqual(s.grade, 89)    # must NOT truncate to 89

    def test_decimal_grade_setter_preserved(self):
        s = Student("Ana", 50)
        s.grade = 72.3
        self.assertAlmostEqual(s.grade, 72.3)

    def test_to_dict_preserves_decimal(self):
        s = Student("Ana", 85.5)
        self.assertEqual(s.to_dict()["grade"], 85.5)

    def test_from_dict_preserves_decimal(self):
        s = Student.from_dict({"name": "Ana", "grade": 85.5})
        self.assertEqual(s.grade, 85.5)

    def test_full_json_round_trip(self):
        """Decimal grade must survive save → load via JsonStorage."""
        storage = self._tmp_storage()
        original = Student("Ana", 92.75)
        storage.save([original])
        loaded = storage.load()
        self.assertEqual(len(loaded), 1)
        self.assertAlmostEqual(loaded[0].grade, 92.75)

    def test_boundary_zero_decimal(self):
        s = Student("Ana", 0.0)
        self.assertEqual(s.grade, 0.0)

    def test_boundary_hundred_decimal(self):
        s = Student("Ana", 100.0)
        self.assertEqual(s.grade, 100.0)

    def test_integer_grade_still_works(self):
        s = Student("Ana", 85)
        self.assertEqual(s.grade, 85.0)

    def test_statistics_with_decimal_grades(self):
        students = [Student(f"S{i}", g) for i, g in enumerate([85.5, 70.0, 59.9])]
        stats = StatisticsService.compute(students)
        self.assertAlmostEqual(stats.average, round((85.5 + 70.0 + 59.9) / 3, 2))
        self.assertAlmostEqual(stats.highest, 85.5)
        self.assertAlmostEqual(stats.lowest, 59.9)

    def test_manager_add_decimal_grade(self):
        mgr = StudentManager(FakeStorage())
        s = mgr.add_student("Ana", 88.8)
        self.assertAlmostEqual(s.grade, 88.8)

    def test_manager_update_decimal_grade(self):
        mgr = StudentManager(FakeStorage())
        mgr.add_student("Ana", 50)
        updated = mgr.update_grade(0, 77.7)
        self.assertAlmostEqual(updated.grade, 77.7)


class TestInvalidGradeValues(unittest.TestCase):
    """Booleans, NaN, infinity, and out-of-range values must be rejected."""

    def test_boolean_true_rejected_by_student(self):
        with self.assertRaises(ValueError):
            Student("Ana", True)

    def test_boolean_false_rejected_by_student(self):
        with self.assertRaises(ValueError):
            Student("Ana", False)

    def test_nan_rejected_by_student(self):
        with self.assertRaises(ValueError):
            Student("Ana", float("nan"))

    def test_inf_rejected_by_student(self):
        with self.assertRaises(ValueError):
            Student("Ana", float("inf"))

    def test_neg_inf_rejected_by_student(self):
        with self.assertRaises(ValueError):
            Student("Ana", float("-inf"))

    def test_string_rejected_by_student(self):
        with self.assertRaises((ValueError, TypeError)):
            Student("Ana", "85")  # type: ignore[arg-type]

    def test_validator_rejects_boolean(self):
        valid, _ = InputValidator.validate_grade(True)
        self.assertFalse(valid)

    def test_validator_rejects_nan(self):
        valid, _ = InputValidator.validate_grade(float("nan"))
        self.assertFalse(valid)

    def test_validator_rejects_inf(self):
        valid, _ = InputValidator.validate_grade(float("inf"))
        self.assertFalse(valid)

    def test_validator_rejects_below_zero(self):
        valid, _ = InputValidator.validate_grade(-0.1)
        self.assertFalse(valid)

    def test_validator_rejects_above_hundred(self):
        valid, _ = InputValidator.validate_grade(100.1)
        self.assertFalse(valid)

    def test_validator_accepts_decimal_in_range(self):
        valid, _ = InputValidator.validate_grade(85.5)
        self.assertTrue(valid)

    def test_grade_setter_rejects_nan(self):
        s = Student("Ana", 50)
        with self.assertRaises(ValueError):
            s.grade = float("nan")

    def test_grade_setter_rejects_boolean(self):
        s = Student("Ana", 50)
        with self.assertRaises(ValueError):
            s.grade = True


# ═════════════════════════════════════════════════════════════════════════════
#  Issue 2 — Grade status threshold boundaries
# ═════════════════════════════════════════════════════════════════════════════

class TestGradeThresholds(unittest.TestCase):
    """Config values must reflect the correct policy.

    Policy:
        90–100  → Excellent
        80–<90  → Good
        70–<80  → Average
        60–<70  → Below Average
        <60     → Failing
    """

    def test_excellent_threshold_is_90(self):
        self.assertEqual(GRADE_EXCELLENT, 90)

    def test_good_threshold_is_80(self):
        self.assertEqual(GRADE_GOOD, 80)

    def test_average_threshold_is_70(self):
        self.assertEqual(GRADE_AVERAGE, 70)

    def test_below_avg_threshold_is_60(self):
        self.assertEqual(GRADE_BELOW_AVG, 60)

    def test_pass_threshold_is_60(self):
        self.assertEqual(StatisticsService.PASS_THRESHOLD, 60)

    # ── Exact boundary values ─────────────────────────────────────────────

    def test_90_is_excellent(self):
        # grade 90.0 must NOT fall into Good
        students = [Student("S", 90)]
        stats = StatisticsService.compute(students)
        self.assertEqual(stats.passing_count, 1)

    def test_89_9_is_not_excellent(self):
        # 89.9 should be Good, not Excellent
        s = Student("S", 89.9)
        self.assertLess(s.grade, GRADE_EXCELLENT)

    def test_80_is_good_not_average(self):
        s = Student("S", 80)
        self.assertGreaterEqual(s.grade, GRADE_GOOD)
        self.assertLess(s.grade, GRADE_EXCELLENT)

    def test_70_is_average_not_below_avg(self):
        s = Student("S", 70)
        self.assertGreaterEqual(s.grade, GRADE_AVERAGE)
        self.assertLess(s.grade, GRADE_GOOD)

    def test_60_is_below_avg_not_failing(self):
        s = Student("S", 60)
        self.assertGreaterEqual(s.grade, GRADE_BELOW_AVG)
        self.assertLess(s.grade, GRADE_AVERAGE)

    def test_60_is_passing(self):
        students = [Student("S", 60)]
        stats = StatisticsService.compute(students)
        self.assertEqual(stats.passing_count, 1)
        self.assertEqual(stats.failing_count, 0)

    def test_59_9_is_failing(self):
        students = [Student("S", 59.9)]
        stats = StatisticsService.compute(students)
        self.assertEqual(stats.failing_count, 1)
        self.assertEqual(stats.passing_count, 0)

    def test_59_is_failing(self):
        students = [Student("S", 59)]
        stats = StatisticsService.compute(students)
        self.assertEqual(stats.failing_count, 1)

    # ── Previously wrong boundary (JS was using 60 for Average, 50 for Below Avg) ──

    def test_65_is_below_avg_not_average(self):
        """65 is in the Below-Average band (60–<70), not Average (70–<80)."""
        s = Student("S", 65)
        self.assertGreaterEqual(s.grade, GRADE_BELOW_AVG)
        self.assertLess(s.grade, GRADE_AVERAGE)

    def test_75_is_average_not_below_avg(self):
        """75 is in the Average band (70–<80)."""
        s = Student("S", 75)
        self.assertGreaterEqual(s.grade, GRADE_AVERAGE)
        self.assertLess(s.grade, GRADE_GOOD)


# ═════════════════════════════════════════════════════════════════════════════
#  Issue 3 — Storage with a bare filename
# ═════════════════════════════════════════════════════════════════════════════

class TestBareFilenameStorage(unittest.TestCase):
    """JsonStorage must work when file_path has no directory component."""

    def setUp(self):
        # Change to a temp directory so bare filename writes go somewhere safe.
        self._orig_dir = os.getcwd()
        self._tmp_dir = tempfile.mkdtemp()
        os.chdir(self._tmp_dir)

    def tearDown(self):
        os.chdir(self._orig_dir)
        # Clean up the temp directory.
        for f in os.listdir(self._tmp_dir):
            try:
                os.unlink(os.path.join(self._tmp_dir, f))
            except OSError:
                pass
        os.rmdir(self._tmp_dir)

    def test_save_bare_filename(self):
        storage = JsonStorage(file_path="grades.json")
        result = storage.save([Student("Ana", 85)])
        self.assertTrue(result)
        self.assertTrue(os.path.exists("grades.json"))

    def test_load_bare_filename_roundtrip(self):
        storage = JsonStorage(file_path="grades.json")
        storage.save([Student("Ana", 85.5)])
        loaded = storage.load()
        self.assertEqual(len(loaded), 1)
        self.assertAlmostEqual(loaded[0].grade, 85.5)

    def test_load_missing_bare_filename_returns_empty(self):
        storage = JsonStorage(file_path="does_not_exist.json")
        self.assertEqual(storage.load(), [])

    def test_atomic_save_bare_filename(self):
        """No stale .tmp files after a successful bare-filename save."""
        storage = JsonStorage(file_path="grades.json")
        storage.save([Student("Ana", 70)])
        tmp_files = [f for f in os.listdir(".") if f.endswith(".tmp")]
        self.assertEqual(tmp_files, [])


# ═════════════════════════════════════════════════════════════════════════════
#  Issue 4 — Duplicate student names and search
# ═════════════════════════════════════════════════════════════════════════════

class TestDuplicateNamesSearch(unittest.TestCase):
    """search_all_by_name must return every student with the queried name."""

    def setUp(self):
        self.mgr = StudentManager(FakeStorage())
        self.mgr.add_student("Alice", 85)
        self.mgr.add_student("Bob", 70)
        self.mgr.add_student("Alice", 92)   # duplicate name, different grade
        self.mgr.add_student("alice", 60)   # same name, different case — NOT a match for exact search
        # Note: "alice" (lowercase) will match case-insensitively.

    def test_search_all_returns_all_exact_matches(self):
        """All students named 'Alice' (case-insensitively) must be returned."""
        matches = self.mgr.search_all_by_name("Alice")
        # Should match "Alice" (index 0), "Alice" (index 2), and "alice" (index 3)
        self.assertEqual(len(matches), 3)

    def test_search_all_returns_indices_and_students(self):
        matches = self.mgr.search_all_by_name("Alice")
        indices = [i for i, _ in matches]
        self.assertIn(0, indices)
        self.assertIn(2, indices)

    def test_search_all_trims_query(self):
        matches = self.mgr.search_all_by_name("  Alice  ")
        self.assertEqual(len(matches), 3)

    def test_search_all_case_insensitive(self):
        matches_lower = self.mgr.search_all_by_name("alice")
        matches_upper = self.mgr.search_all_by_name("ALICE")
        self.assertEqual(len(matches_lower), len(matches_upper))
        self.assertEqual(len(matches_lower), 3)

    def test_search_all_not_found_returns_empty(self):
        matches = self.mgr.search_all_by_name("Zain")
        self.assertEqual(matches, [])

    def test_search_by_name_first_match_unchanged(self):
        """Original search_by_name must still return the first match index."""
        first_index = self.mgr.search_by_name("Alice")
        self.assertEqual(first_index, 0)

    def test_search_by_name_not_found_returns_minus_one(self):
        self.assertEqual(self.mgr.search_by_name("Nobody"), -1)

    def test_duplicate_students_have_different_uuids(self):
        """Two students with the same name must have distinct UUIDs."""
        matches = self.mgr.search_all_by_name("Alice")
        ids = [s.id for _, s in matches]
        self.assertEqual(len(ids), len(set(ids)))

    def test_update_one_duplicate_does_not_affect_other(self):
        """Updating one Alice by index must not change the other Alice."""
        matches_before = self.mgr.search_all_by_name("Alice")
        # Grab both Alice entries (indices 0 and 2 given setUp order).
        idx0, s0 = matches_before[0]
        idx2, s2 = matches_before[1]
        uuid0, uuid2 = s0.id, s2.id

        # Update the first Alice.
        self.mgr.update_grade(idx0, 55)

        matches_after = self.mgr.search_all_by_name("Alice")
        after_by_uuid = {s.id: s for _, s in matches_after}

        self.assertAlmostEqual(after_by_uuid[uuid0].grade, 55)
        self.assertAlmostEqual(after_by_uuid[uuid2].grade, s2.grade)  # unchanged

    def test_remove_one_duplicate_keeps_other(self):
        """Removing one Alice by index must leave the other intact."""
        matches_before = self.mgr.search_all_by_name("Alice")
        idx0, s0 = matches_before[0]
        kept_uuid = matches_before[1][1].id

        self.mgr.remove_student(idx0)

        remaining_ids = [s.id for s in self.mgr.get_all_students()]
        self.assertIn(kept_uuid, remaining_ids)
        self.assertNotIn(s0.id, remaining_ids)

    def test_student_equality_by_uuid(self):
        """Two Student objects are equal iff they share the same UUID."""
        a = Student("Alice", 85)
        b = Student("Alice", 85)
        self.assertNotEqual(a, b)   # different UUIDs → not equal

        c = Student.from_dict(a.to_dict())
        self.assertEqual(a, c)      # same UUID (round-trip) → equal


if __name__ == "__main__":
    unittest.main()
