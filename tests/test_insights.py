"""Tests for InsightsService — per-student support flags."""

import unittest

from app.config import PASSING_THRESHOLD
from app.models.student import Student
from app.services.insights_service import InsightsService


def make_student(name: str, grade: float) -> Student:
    return Student(name=name, grade=grade)


class TestInsightsServiceEmpty(unittest.TestCase):
    """Empty roster produces no insights."""

    def test_empty_returns_empty_list(self):
        result = InsightsService.get_insights([])
        self.assertEqual(result, [])


class TestInsightsServiceFlags(unittest.TestCase):
    """Flag logic and reasons match the shared PASSING_THRESHOLD."""

    def test_below_threshold_is_needs_attention(self):
        s = make_student("Alice", PASSING_THRESHOLD - 1)
        result = InsightsService.get_insights([s])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].status, "needs_attention")

    def test_at_threshold_is_passing(self):
        s = make_student("Bob", PASSING_THRESHOLD)
        result = InsightsService.get_insights([s])
        self.assertEqual(result[0].status, "passing")

    def test_above_threshold_is_passing(self):
        s = make_student("Carol", PASSING_THRESHOLD + 1)
        result = InsightsService.get_insights([s])
        self.assertEqual(result[0].status, "passing")

    def test_reason_contains_grade_and_threshold(self):
        grade = PASSING_THRESHOLD - 5
        s = make_student("Dave", grade)
        result = InsightsService.get_insights([s])
        self.assertIn(str(grade), result[0].reason)
        self.assertIn(str(PASSING_THRESHOLD), result[0].reason)

    def test_threshold_field_matches_config(self):
        s = make_student("Eve", 75)
        result = InsightsService.get_insights([s])
        self.assertEqual(result[0].threshold, PASSING_THRESHOLD)


class TestInsightsServiceOrdering(unittest.TestCase):
    """needs_attention students appear first, then passing; within each group sorted by grade."""

    def test_needs_attention_before_passing(self):
        students = [
            make_student("High", 90),
            make_student("Low", 40),
            make_student("Mid", 70),
            make_student("Fail", 55),
        ]
        result = InsightsService.get_insights(students)
        statuses = [i.status for i in result]
        # All needs_attention entries come before passing entries.
        seen_passing = False
        for s in statuses:
            if s == "passing":
                seen_passing = True
            if s == "needs_attention" and seen_passing:
                self.fail("needs_attention appeared after passing")

    def test_needs_attention_sorted_by_grade_ascending(self):
        students = [
            make_student("A", 55),
            make_student("B", 40),
            make_student("C", 48),
        ]
        result = InsightsService.get_insights(students)
        flagged_grades = [i.grade for i in result if i.status == "needs_attention"]
        self.assertEqual(flagged_grades, sorted(flagged_grades))

    def test_student_id_and_name_preserved(self):
        s = make_student("Frank", 30)
        result = InsightsService.get_insights([s])
        self.assertEqual(result[0].student_id, s.id)
        self.assertEqual(result[0].name, "Frank")


if __name__ == "__main__":
    unittest.main()
