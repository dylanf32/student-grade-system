"""
Tests for A2 — Assignments and weighted grades.

Covers:
  - Category/Assignment/EnrollmentGrade model validation
  - GradebookService CRUD (categories, assignments, scores)
  - Category grade calculation (earned/possible for scored only)
  - Class grade calculation (renormalized weighted average)
  - Provisional flag (any positive-weight assignment ungraded)
  - Edge cases: zero score, null score, empty category, zero-weight category
  - Invalid inputs (boolean score, out-of-range, infinite, non-numeric)
  - Term GPA (credit-weighted, matching grade-point boundaries)
  - One student with different grades in two classes
  - JsonStorage v3 round trip (categories and enrollment_grades survive)
  - JsonStorage v2 backward compatibility (no categories/enrollment_grades in file)
"""

from __future__ import annotations

import json
import uuid
from typing import List

import pytest

from app.models.gradebook import Assignment, Category, EnrollmentGrade
from app.models.class_record import ClassRecord
from app.services.gradebook_service import GradebookService, _grade_to_points
from app.storage.json_storage import JsonStorage
from app.models.student import Student
from app.services.class_manager import ClassManager


# ══════════════════════════════════════════════════════════════════════════════
#  Assignment model validation
# ══════════════════════════════════════════════════════════════════════════════

class TestAssignmentModel:
    def test_basic(self):
        a = Assignment(name="HW1", possible=100)
        assert a.name == "HW1"
        assert a.possible == 100.0
        assert a.id

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="empty"):
            Assignment(name="", possible=10)

    def test_zero_possible_raises(self):
        with pytest.raises(ValueError, match="positive"):
            Assignment(name="HW1", possible=0)

    def test_negative_possible_raises(self):
        with pytest.raises(ValueError, match="positive"):
            Assignment(name="HW1", possible=-5)

    def test_boolean_possible_raises(self):
        with pytest.raises(ValueError):
            Assignment(name="HW1", possible=True)

    def test_inf_possible_raises(self):
        with pytest.raises(ValueError, match="finite"):
            Assignment(name="HW1", possible=float("inf"))

    def test_stable_id(self):
        fixed = str(uuid.uuid4())
        a = Assignment(name="HW1", possible=10, assignment_id=fixed)
        assert a.id == fixed

    def test_round_trip(self):
        a = Assignment(name="Quiz 1", possible=25.5)
        d = a.to_dict()
        a2 = Assignment.from_dict(d)
        assert a2.id == a.id
        assert a2.name == "Quiz 1"
        assert a2.possible == 25.5


# ══════════════════════════════════════════════════════════════════════════════
#  Category model validation
# ══════════════════════════════════════════════════════════════════════════════

class TestCategoryModel:
    def _cid(self):
        return str(uuid.uuid4())

    def test_basic(self):
        c = Category(class_id=self._cid(), name="Homework", weight=30.0)
        assert c.name == "Homework"
        assert c.weight == 30.0

    def test_empty_class_id_raises(self):
        with pytest.raises(ValueError):
            Category(class_id="", name="HW", weight=10)

    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="empty"):
            Category(class_id=self._cid(), name="", weight=10)

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="non-negative"):
            Category(class_id=self._cid(), name="HW", weight=-1)

    def test_zero_weight_allowed(self):
        c = Category(class_id=self._cid(), name="Bonus", weight=0)
        assert c.weight == 0.0

    def test_boolean_weight_raises(self):
        with pytest.raises(ValueError):
            Category(class_id=self._cid(), name="HW", weight=True)

    def test_inf_weight_raises(self):
        with pytest.raises(ValueError, match="finite"):
            Category(class_id=self._cid(), name="HW", weight=float("inf"))

    def test_add_assignment(self):
        c = Category(class_id=self._cid(), name="HW", weight=50)
        a = Assignment(name="HW1", possible=10)
        c.add_assignment(a)
        assert len(c.assignments) == 1

    def test_add_duplicate_ignored(self):
        c = Category(class_id=self._cid(), name="HW", weight=50)
        a = Assignment(name="HW1", possible=10)
        c.add_assignment(a)
        c.add_assignment(a)  # same id, no-op
        assert len(c.assignments) == 1

    def test_remove_assignment(self):
        c = Category(class_id=self._cid(), name="HW", weight=50)
        a = Assignment(name="HW1", possible=10)
        c.add_assignment(a)
        c.remove_assignment(a.id)
        assert c.assignments == []

    def test_round_trip(self):
        cid = self._cid()
        cat = Category(class_id=cid, name="Exams", weight=40.0)
        asn = Assignment(name="Midterm", possible=100)
        cat.add_assignment(asn)
        d = cat.to_dict()
        cat2 = Category.from_dict(d)
        assert cat2.id == cat.id
        assert cat2.class_id == cid
        assert cat2.weight == 40.0
        assert len(cat2.assignments) == 1
        assert cat2.assignments[0].id == asn.id


# ══════════════════════════════════════════════════════════════════════════════
#  EnrollmentGrade model validation
# ══════════════════════════════════════════════════════════════════════════════

class TestEnrollmentGradeModel:
    def test_set_and_get_score(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        eg.set_score("a1", 80.0, possible=100)
        assert eg.get_score("a1") == 80.0

    def test_null_score_allowed(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        eg.set_score("a1", None, possible=100)
        assert eg.get_score("a1") is None

    def test_zero_score_allowed(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        eg.set_score("a1", 0.0, possible=100)
        assert eg.get_score("a1") == 0.0

    def test_score_exceeds_possible_raises(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        with pytest.raises(ValueError, match="exceeds"):
            eg.set_score("a1", 101.0, possible=100)

    def test_negative_score_raises(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        with pytest.raises(ValueError, match="negative"):
            eg.set_score("a1", -1.0, possible=100)

    def test_boolean_score_raises(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        with pytest.raises(ValueError, match="boolean"):
            eg.set_score("a1", True, possible=100)

    def test_inf_score_raises(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        with pytest.raises(ValueError, match="finite"):
            eg.set_score("a1", float("inf"), possible=100)

    def test_get_unset_returns_none(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        assert eg.get_score("ghost") is None

    def test_round_trip(self):
        eg = EnrollmentGrade(student_id="s1", class_id="c1")
        eg.set_score("a1", 75.0, possible=100)
        eg.set_score("a2", None, possible=50)
        d = eg.to_dict()
        eg2 = EnrollmentGrade.from_dict(d)
        assert eg2.student_id == "s1"
        assert eg2.class_id == "c1"
        assert eg2.get_score("a1") == 75.0
        assert eg2.get_score("a2") is None


# ══════════════════════════════════════════════════════════════════════════════
#  GradebookService — category grade
# ══════════════════════════════════════════════════════════════════════════════

class TestCategoryGrade:
    """category_result: earned/possible across scored assignments only."""

    def setup_method(self):
        self.svc = GradebookService()
        self.class_id = str(uuid.uuid4())
        self.student_id = str(uuid.uuid4())

    def _add_cat(self, weight=50.0) -> Category:
        return self.svc.add_category(self.class_id, "HW", weight)

    def test_all_scored(self):
        cat = self._add_cat()
        a1 = self.svc.add_assignment(cat.id, "HW1", 100)
        a2 = self.svc.add_assignment(cat.id, "HW2", 50)
        self.svc.set_score(self.student_id, self.class_id, a1.id, 80)
        self.svc.set_score(self.student_id, self.class_id, a2.id, 40)
        # (80+40)/(100+50)*100 = 120/150*100 = 80.0
        res = self.svc.category_result(self.student_id, cat)
        assert res["grade"] == pytest.approx(80.0)
        assert res["provisional"] is False
        assert res["scored"] == 2

    def test_unequal_weights_and_points(self):
        """Two assignments with different possible points."""
        cat = self._add_cat()
        a1 = self.svc.add_assignment(cat.id, "Big", 200)
        a2 = self.svc.add_assignment(cat.id, "Small", 10)
        self.svc.set_score(self.student_id, self.class_id, a1.id, 100)
        self.svc.set_score(self.student_id, self.class_id, a2.id, 10)
        # (100+10)/(200+10)*100 = 110/210*100 ≈ 52.38
        res = self.svc.category_result(self.student_id, cat)
        assert res["grade"] == pytest.approx(110 / 210 * 100, abs=0.01)

    def test_partial_scored_provisional(self):
        cat = self._add_cat()
        a1 = self.svc.add_assignment(cat.id, "HW1", 100)
        a2 = self.svc.add_assignment(cat.id, "HW2", 100)
        self.svc.set_score(self.student_id, self.class_id, a1.id, 70)
        # a2 not scored
        res = self.svc.category_result(self.student_id, cat)
        assert res["grade"] == pytest.approx(70.0)  # only a1 counts
        assert res["provisional"] is True

    def test_none_scored_returns_null(self):
        cat = self._add_cat()
        self.svc.add_assignment(cat.id, "HW1", 100)
        res = self.svc.category_result(self.student_id, cat)
        assert res["grade"] is None
        assert res["provisional"] is True

    def test_zero_score_graded(self):
        cat = self._add_cat()
        a1 = self.svc.add_assignment(cat.id, "HW1", 100)
        self.svc.set_score(self.student_id, self.class_id, a1.id, 0.0)
        res = self.svc.category_result(self.student_id, cat)
        assert res["grade"] == pytest.approx(0.0)
        assert res["provisional"] is False  # graded zero is not provisional

    def test_empty_category_no_grade(self):
        cat = self._add_cat()
        res = self.svc.category_result(self.student_id, cat)
        assert res["grade"] is None
        assert res["provisional"] is False
        assert res["total"] == 0


# ══════════════════════════════════════════════════════════════════════════════
#  GradebookService — class grade (weighted)
# ══════════════════════════════════════════════════════════════════════════════

class TestClassGrade:
    """class_result: renormalized weighted average over categories with scored work."""

    def setup_method(self):
        self.svc = GradebookService()
        self.class_id = str(uuid.uuid4())
        self.sid = str(uuid.uuid4())

    def _score_all(self, cat: Category, score: float, possible: float) -> None:
        """Add one assignment to cat and score it."""
        asn = self.svc.add_assignment(cat.id, "A", possible)
        self.svc.set_score(self.sid, self.class_id, asn.id, score)

    def test_single_category_full_score(self):
        cat = self.svc.add_category(self.class_id, "HW", 100)
        self._score_all(cat, 80, 100)
        res = self.svc.class_result(self.sid, self.class_id)
        assert res["grade"] == pytest.approx(80.0)
        assert res["provisional"] is False

    def test_two_categories_equal_weight(self):
        c1 = self.svc.add_category(self.class_id, "HW", 50)
        c2 = self.svc.add_category(self.class_id, "Exams", 50)
        self._score_all(c1, 90, 100)
        self._score_all(c2, 70, 100)
        res = self.svc.class_result(self.sid, self.class_id)
        assert res["grade"] == pytest.approx(80.0)

    def test_renormalization_partial_scored(self):
        """If only one of two equal-weight categories has scored work,
        grade equals that category's grade (renormalized over its weight only)."""
        c1 = self.svc.add_category(self.class_id, "HW", 50)
        c2 = self.svc.add_category(self.class_id, "Exams", 50)
        self._score_all(c1, 60, 100)
        # c2 has an assignment but no score → grade=None
        self.svc.add_assignment(c2.id, "Midterm", 100)
        res = self.svc.class_result(self.sid, self.class_id)
        assert res["grade"] == pytest.approx(60.0)  # renorm: 50*60/50
        assert res["provisional"] is True

    def test_zero_weight_category_excluded(self):
        """Zero-weight category does not contribute to grade or provisional."""
        c1 = self.svc.add_category(self.class_id, "Main", 100)
        c2 = self.svc.add_category(self.class_id, "Bonus", 0)
        self._score_all(c1, 75, 100)
        # bonus has unscored assignment
        self.svc.add_assignment(c2.id, "Extra", 10)
        res = self.svc.class_result(self.sid, self.class_id)
        assert res["grade"] == pytest.approx(75.0)
        assert res["provisional"] is False  # bonus (weight=0) doesn't count

    def test_no_scored_work_returns_null(self):
        cat = self.svc.add_category(self.class_id, "HW", 100)
        self.svc.add_assignment(cat.id, "HW1", 100)
        res = self.svc.class_result(self.sid, self.class_id)
        assert res["grade"] is None
        assert res["provisional"] is True

    def test_empty_class_returns_null_not_provisional(self):
        """A class with no categories at all has no grade and is not provisional."""
        res = self.svc.class_result(self.sid, self.class_id)
        assert res["grade"] is None
        assert res["provisional"] is False

    def test_unequal_weights_renormalized(self):
        """60%/40% weights, only 60% category has scored work → grade = that cat's grade."""
        c1 = self.svc.add_category(self.class_id, "HW", 60)
        c2 = self.svc.add_category(self.class_id, "Exams", 40)
        self._score_all(c1, 90, 100)  # cat1 grade = 90
        # c2 no score
        self.svc.add_assignment(c2.id, "Exam", 100)
        res = self.svc.class_result(self.sid, self.class_id)
        assert res["grade"] == pytest.approx(90.0)  # renorm 60*90/60

    def test_invalid_score_not_boolean(self):
        cat = self.svc.add_category(self.class_id, "HW", 100)
        asn = self.svc.add_assignment(cat.id, "HW1", 100)
        with pytest.raises(ValueError, match="boolean"):
            self.svc.set_score(self.sid, self.class_id, asn.id, True)

    def test_score_out_of_range_raises(self):
        cat = self.svc.add_category(self.class_id, "HW", 100)
        asn = self.svc.add_assignment(cat.id, "HW1", 100)
        with pytest.raises(ValueError, match="exceeds"):
            self.svc.set_score(self.sid, self.class_id, asn.id, 150)

    def test_score_unknown_assignment_raises(self):
        with pytest.raises(ValueError, match="not found"):
            self.svc.set_score(self.sid, self.class_id, "ghost-id", 50)


# ══════════════════════════════════════════════════════════════════════════════
#  GradebookService — one student, two classes
# ══════════════════════════════════════════════════════════════════════════════

class TestTwoClasses:
    """A student with different grades in two separate classes."""

    def setup_method(self):
        self.svc = GradebookService()
        self.sid = str(uuid.uuid4())
        self.class_a = str(uuid.uuid4())
        self.class_b = str(uuid.uuid4())

    def test_class_isolation(self):
        cat_a = self.svc.add_category(self.class_a, "HW", 100)
        cat_b = self.svc.add_category(self.class_b, "HW", 100)
        asn_a = self.svc.add_assignment(cat_a.id, "HW1", 100)
        asn_b = self.svc.add_assignment(cat_b.id, "HW1", 100)
        self.svc.set_score(self.sid, self.class_a, asn_a.id, 90)
        self.svc.set_score(self.sid, self.class_b, asn_b.id, 60)

        res_a = self.svc.class_result(self.sid, self.class_a)
        res_b = self.svc.class_result(self.sid, self.class_b)
        assert res_a["grade"] == pytest.approx(90.0)
        assert res_b["grade"] == pytest.approx(60.0)

    def test_term_gpa_credit_weighted(self):
        """3-credit class at 90 (4.0) and 4-credit class at 60 (1.0)."""
        cr_a = ClassRecord(code="CS1", title="A", credits=3.0,
                           class_id=self.class_a)
        cr_b = ClassRecord(code="MA1", title="B", credits=4.0,
                           class_id=self.class_b)

        cat_a = self.svc.add_category(self.class_a, "HW", 100)
        cat_b = self.svc.add_category(self.class_b, "HW", 100)
        asn_a = self.svc.add_assignment(cat_a.id, "HW", 100)
        asn_b = self.svc.add_assignment(cat_b.id, "HW", 100)
        self.svc.set_score(self.sid, self.class_a, asn_a.id, 90)  # 4.0
        self.svc.set_score(self.sid, self.class_b, asn_b.id, 60)  # 1.0

        # (3*4.0 + 4*1.0) / 7 = (12+4)/7 = 16/7 ≈ 2.29
        gpa = self.svc.term_gpa(self.sid, [cr_a, cr_b])
        assert gpa == pytest.approx(16 / 7, abs=0.01)

    def test_term_gpa_null_class_excluded(self):
        """A class with no scored work does not contribute to term GPA."""
        cr_a = ClassRecord(code="CS1", title="A", credits=3.0,
                           class_id=self.class_a)
        cr_b = ClassRecord(code="MA1", title="B", credits=4.0,
                           class_id=self.class_b)

        cat_a = self.svc.add_category(self.class_a, "HW", 100)
        asn_a = self.svc.add_assignment(cat_a.id, "HW", 100)
        self.svc.set_score(self.sid, self.class_a, asn_a.id, 80)  # 3.0
        # class_b has no scored work → null grade

        gpa = self.svc.term_gpa(self.sid, [cr_a, cr_b])
        assert gpa == pytest.approx(3.0)

    def test_term_gpa_no_grades_returns_none(self):
        cr_a = ClassRecord(code="CS1", title="A", credits=3.0, class_id=self.class_a)
        gpa = self.svc.term_gpa(self.sid, [cr_a])
        assert gpa is None


# ══════════════════════════════════════════════════════════════════════════════
#  Grade-point boundaries
# ══════════════════════════════════════════════════════════════════════════════

class TestGradeToPoints:
    def test_boundaries(self):
        assert _grade_to_points(100) == 4.0
        assert _grade_to_points(90)  == 4.0
        assert _grade_to_points(89)  == 3.0
        assert _grade_to_points(80)  == 3.0
        assert _grade_to_points(79)  == 2.0
        assert _grade_to_points(70)  == 2.0
        assert _grade_to_points(69)  == 1.0
        assert _grade_to_points(60)  == 1.0
        assert _grade_to_points(59)  == 0.0
        assert _grade_to_points(0)   == 0.0


# ══════════════════════════════════════════════════════════════════════════════
#  JsonStorage — v3 round trip
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonStorageV3RoundTrip:
    def test_full_gradebook_round_trip(self, tmp_path):
        p = str(tmp_path / "dataset.json")
        storage = JsonStorage(file_path=p)

        svc = GradebookService()
        class_id = str(uuid.uuid4())
        sid = str(uuid.uuid4())

        cat = svc.add_category(class_id, "Homework", 60.0)
        cat2 = svc.add_category(class_id, "Exams", 40.0)
        a1 = svc.add_assignment(cat.id, "HW1", 100)
        a2 = svc.add_assignment(cat2.id, "Midterm", 200)
        svc.set_score(sid, class_id, a1.id, 85)
        svc.set_score(sid, class_id, a2.id, 160)

        ok = storage.save_dataset(
            students=[],
            classes=[],
            enrollments=[],
            categories=svc.categories_to_list(),
            enrollment_grades=svc.enrollment_grades_to_list(),
        )
        assert ok

        payload = storage.load_dataset()
        assert len(payload.categories) == 2
        assert len(payload.enrollment_grades) == 1

        # reload into fresh service
        svc2 = GradebookService()
        svc2.load_from_data(payload.categories, payload.enrollment_grades)

        cat_loaded = svc2.get_category(cat.id)
        assert cat_loaded is not None
        assert cat_loaded.name == "Homework"
        assert cat_loaded.weight == 60.0
        assert len(cat_loaded.assignments) == 1

        score = svc2.get_score(sid, class_id, a1.id)
        assert score == 85.0
        score2 = svc2.get_score(sid, class_id, a2.id)
        assert score2 == 160.0

        # class grade survives round-trip
        res = svc2.class_result(sid, class_id)
        # cat1: 85/100 = 85%; cat2: 160/200 = 80%
        # weighted: (60*85 + 40*80)/100 = (5100+3200)/100 = 83.0
        assert res["grade"] == pytest.approx(83.0)

    def test_v3_file_has_version_3(self, tmp_path):
        p = str(tmp_path / "dataset.json")
        storage = JsonStorage(file_path=p)
        storage.save_dataset(students=[], classes=[], enrollments=[],
                             categories=[], enrollment_grades=[])
        with open(p, "r", encoding="utf-8") as f:
            raw = json.load(f)
        assert raw.get("version") == 3
        assert "categories" in raw
        assert "enrollment_grades" in raw


# ══════════════════════════════════════════════════════════════════════════════
#  JsonStorage — v2 backward compatibility
# ══════════════════════════════════════════════════════════════════════════════

class TestJsonStorageV2BackwardCompat:
    def test_v2_file_loads_empty_gradebook(self, tmp_path):
        """A v2 file (no categories/enrollment_grades keys) loads fine."""
        p = str(tmp_path / "dataset.json")
        v2_data = {
            "version": 2,
            "students": [],
            "classes": [{"id": str(uuid.uuid4()), "code": "CS1", "title": "T", "credits": 3.0}],
            "enrollments": [],
        }
        with open(p, "w") as f:
            json.dump(v2_data, f)

        storage = JsonStorage(file_path=p)
        payload = storage.load_dataset()

        assert len(payload.classes) == 1
        assert payload.categories == []
        assert payload.enrollment_grades == []
