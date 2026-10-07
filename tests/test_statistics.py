"""
Unit tests for the StatisticsService.
"""

import unittest

from app.models.student import Student
from app.services.statistics_service import StatisticsService


class TestStatisticsCompute(unittest.TestCase):
    """Tests for StatisticsService.compute()."""

    def _make_students(self, grades):
        return [Student(f"Student{i}", g) for i, g in enumerate(grades)]

    def test_compute_normal(self):
        students = self._make_students([80, 90, 70])
        stats = StatisticsService.compute(students)
        self.assertEqual(stats.total_students, 3)
        self.assertEqual(stats.average, 80.0)
        self.assertEqual(stats.highest, 90)
        self.assertEqual(stats.lowest, 70)
        self.assertEqual(stats.passing_count, 3)
        self.assertEqual(stats.failing_count, 0)

    def test_compute_with_failing(self):
        students = self._make_students([90, 50, 40])
        stats = StatisticsService.compute(students)
        self.assertEqual(stats.passing_count, 1)
        self.assertEqual(stats.failing_count, 2)

    def test_compute_empty(self):
        stats = StatisticsService.compute([])
        self.assertEqual(stats.total_students, 0)
        self.assertEqual(stats.average, 0.0)

    def test_compute_single(self):
        students = self._make_students([75])
        stats = StatisticsService.compute(students)
        self.assertEqual(stats.average, 75.0)
        self.assertEqual(stats.highest, 75)
        self.assertEqual(stats.lowest, 75)


class TestStatisticsAccessors(unittest.TestCase):
    """Tests for individual statistic accessors."""

    def setUp(self):
        self.students = [
            Student("Ali", 80),
            Student("Sara", 95),
            Student("Ahmed", 70),
        ]

    def test_get_average(self):
        self.assertEqual(StatisticsService.get_average(self.students), 81.67)

    def test_get_highest(self):
        self.assertEqual(StatisticsService.get_highest(self.students), 95)

    def test_get_lowest(self):
        self.assertEqual(StatisticsService.get_lowest(self.students), 70)

    def test_get_sorted_ascending(self):
        result = StatisticsService.get_sorted(self.students, ascending=True)
        grades = [s.grade for s in result]
        self.assertEqual(grades, [70, 80, 95])

    def test_get_sorted_descending(self):
        result = StatisticsService.get_sorted(self.students, ascending=False)
        grades = [s.grade for s in result]
        self.assertEqual(grades, [95, 80, 70])

    def test_get_sorted_does_not_mutate(self):
        """Ensures sorting returns a new list, not mutating the original."""
        original_grades = [s.grade for s in self.students]
        StatisticsService.get_sorted(self.students, ascending=True)
        current_grades = [s.grade for s in self.students]
        self.assertEqual(original_grades, current_grades)


class TestStatisticsEmpty(unittest.TestCase):
    """Tests for edge case: empty student list."""

    def test_average_empty(self):
        self.assertEqual(StatisticsService.get_average([]), 0.0)

    def test_highest_empty(self):
        self.assertIsNone(StatisticsService.get_highest([]))

    def test_lowest_empty(self):
        self.assertIsNone(StatisticsService.get_lowest([]))


if __name__ == "__main__":
    unittest.main()
