"""
GradebookService — calculations for weighted grades and term GPA.

Responsibilities
----------------
  - Manage categories and assignments per class.
  - Manage per-enrollment scores.
  - Calculate per-category grades, per-class weighted grades, and term GPA.
  - Return provisional flag when any assignment in a category is ungraded.

Calculation rules (A2 spec)
---------------------------
  Category grade  = total earned / total possible across *scored* assignments.
                    Assignments with a null score are skipped (ungraded).
                    If no assignment in the category has been scored → null.

  Class grade     = weighted average of category grades, renormalized over
                    categories that have positive weight AND have at least one
                    scored assignment (i.e. a non-null category grade).
                    If no such category exists → null.

  Provisional     = True if any assignment in any positive-weight category
                    is ungraded (score is None); False otherwise.
                    A class with no assignments is not provisional.

  Term GPA        = credit-weighted average of grade points for all classes
                    where the student has a non-null class grade, using the
                    standard boundaries from app.config and Student.
                    Separate from manual cumulative GPA on Student.

Grade-point mapping (matches Student.compute_gpa_from_courses):
  90–100 → 4.0,  80–<90 → 3.0,  70–<80 → 2.0,  60–<70 → 1.0,  <60 → 0.0
"""

from __future__ import annotations

import threading
from typing import Dict, List, Optional, Tuple

from app.models.gradebook import Category, Assignment, EnrollmentGrade
from app.models.class_record import ClassRecord


class GradebookService:
    """Manages categories, assignments, and per-enrollment scores for all classes.

    Thread safety: a single lock guards all mutable state.

    Attributes:
        _categories  (Dict[str, Category]):       category_id → Category
        _enrollment_grades                        (student_id, class_id) → EnrollmentGrade
        _lock        (threading.Lock)
    """

    def __init__(self) -> None:
        self._categories: Dict[str, Category] = {}
        self._enrollment_grades: Dict[Tuple[str, str], EnrollmentGrade] = {}
        self._lock = threading.Lock()

    # ══════════════════════════════════════════════════════════════════════════
    #  Category management
    # ══════════════════════════════════════════════════════════════════════════

    def add_category(
        self, class_id: str, name: str, weight: float
    ) -> Category:
        """Create and store a new Category for a class.

        Raises:
            ValueError: On invalid class_id/name/weight.
        """
        cat = Category(class_id=class_id, name=name, weight=weight)
        with self._lock:
            self._categories[cat.id] = cat
        return cat

    def get_category(self, category_id: str) -> Optional[Category]:
        with self._lock:
            return self._categories.get(category_id)

    def get_categories_for_class(self, class_id: str) -> List[Category]:
        """Returns all categories belonging to the given class."""
        with self._lock:
            return [c for c in self._categories.values() if c.class_id == class_id]

    def update_category(self, category_id: str, **fields) -> Category:
        """Update name and/or weight on a category.

        Validates the complete new weight configuration before applying.

        Raises:
            ValueError: If category not found or value invalid.
        """
        with self._lock:
            cat = self._categories.get(category_id)
            if cat is None:
                raise ValueError(f"Category not found: {category_id}")
            # apply via setters (they validate)
            if "name" in fields:
                cat.name = fields["name"]
            if "weight" in fields:
                cat.weight = fields["weight"]
            return cat

    def delete_category(self, category_id: str) -> Category:
        """Remove a category and all its assignments.

        Also removes any scores for assignments in this category.

        Raises:
            ValueError: If not found.
        """
        with self._lock:
            cat = self._categories.get(category_id)
            if cat is None:
                raise ValueError(f"Category not found: {category_id}")
            # clean up scores for assignments in this category
            assignment_ids = {a.id for a in cat.assignments}
            for key, eg in list(self._enrollment_grades.items()):
                if eg.class_id == cat.class_id:
                    for aid in assignment_ids:
                        eg._scores.pop(aid, None)
            del self._categories[category_id]
        return cat

    # ══════════════════════════════════════════════════════════════════════════
    #  Assignment management
    # ══════════════════════════════════════════════════════════════════════════

    def add_assignment(
        self, category_id: str, name: str, possible: float
    ) -> Assignment:
        """Add a new assignment to the given category.

        Raises:
            ValueError: If category not found or name/possible invalid.
        """
        with self._lock:
            cat = self._categories.get(category_id)
            if cat is None:
                raise ValueError(f"Category not found: {category_id}")
            asn = Assignment(name=name, possible=possible)
            cat.add_assignment(asn)
            return asn

    def remove_assignment(self, category_id: str, assignment_id: str) -> None:
        """Remove an assignment and clean up its scores.

        Raises:
            ValueError: If category not found.
        """
        with self._lock:
            cat = self._categories.get(category_id)
            if cat is None:
                raise ValueError(f"Category not found: {category_id}")
            cat.remove_assignment(assignment_id)
            # remove scores for this assignment
            for eg in self._enrollment_grades.values():
                eg._scores.pop(assignment_id, None)

    # ══════════════════════════════════════════════════════════════════════════
    #  Score management
    # ══════════════════════════════════════════════════════════════════════════

    def set_score(
        self,
        student_id: str,
        class_id: str,
        assignment_id: str,
        score: Optional[float],
    ) -> None:
        """Record or update a score.

        Locates the assignment's possible points automatically.

        Raises:
            ValueError: If assignment not found in any category for this class,
                        or the score is invalid.
        """
        with self._lock:
            possible = self._find_possible(class_id, assignment_id)
            if possible is None:
                raise ValueError(
                    f"Assignment {assignment_id} not found in class {class_id}."
                )
            key = (student_id, class_id)
            if key not in self._enrollment_grades:
                self._enrollment_grades[key] = EnrollmentGrade(student_id, class_id)
            self._enrollment_grades[key].set_score(assignment_id, score, possible)

    def get_score(
        self, student_id: str, class_id: str, assignment_id: str
    ) -> Optional[float]:
        """Returns the score, or None if not set."""
        with self._lock:
            key = (student_id, class_id)
            eg = self._enrollment_grades.get(key)
            if eg is None:
                return None
            return eg.get_score(assignment_id)

    def remove_enrollment_scores(self, student_id: str, class_id: str) -> None:
        """Remove all scores for a student/class pair (called on unenroll)."""
        with self._lock:
            self._enrollment_grades.pop((student_id, class_id), None)

    # ══════════════════════════════════════════════════════════════════════════
    #  Grade calculations
    # ══════════════════════════════════════════════════════════════════════════

    def category_result(
        self, student_id: str, category: Category
    ) -> dict:
        """Calculate a student's grade for one category.

        Returns a dict:
          {
            "grade":       float | None   # earned/possible across scored; None if none scored
            "provisional": bool           # True if any assignment has no score
            "scored":      int            # number of assignments with a score
            "total":       int            # total assignments in the category
          }
        """
        with self._lock:
            return self._category_result_locked(student_id, category)

    def _category_result_locked(
        self, student_id: str, category: Category
    ) -> dict:
        assignments = category.assignments
        if not assignments:
            return {"grade": None, "provisional": False, "scored": 0, "total": 0}

        key = (student_id, category.class_id)
        eg = self._enrollment_grades.get(key)

        earned = 0.0
        possible_total = 0.0
        scored = 0
        provisional = False

        for asn in assignments:
            score = eg.get_score(asn.id) if eg else None
            if score is None:
                provisional = True
            else:
                earned += score
                possible_total += asn.possible
                scored += 1

        if possible_total == 0:
            grade = None
        else:
            grade = earned / possible_total * 100.0

        return {
            "grade": grade,
            "provisional": provisional,
            "scored": scored,
            "total": len(assignments),
        }

    def class_result(
        self, student_id: str, class_id: str
    ) -> dict:
        """Calculate a student's overall weighted grade for a class.

        Returns a dict:
          {
            "grade":       float | None   # weighted average (0–100) or None
            "provisional": bool           # True if any positive-weight assignment ungraded
            "categories":  list of per-category result dicts with 'category_id' added
          }
        """
        with self._lock:
            categories = [
                c for c in self._categories.values() if c.class_id == class_id
            ]

            cat_results = []
            total_weight = 0.0
            weighted_sum = 0.0
            overall_provisional = False

            for cat in categories:
                res = self._category_result_locked(student_id, cat)
                res["category_id"] = cat.id
                res["name"] = cat.name
                res["weight"] = cat.weight
                cat_results.append(res)

                if cat.weight > 0 and res["provisional"]:
                    overall_provisional = True
                if cat.weight > 0 and res["grade"] is not None:
                    total_weight += cat.weight
                    weighted_sum += cat.weight * res["grade"]

            if total_weight == 0:
                overall_grade = None
            else:
                overall_grade = weighted_sum / total_weight

            return {
                "grade": overall_grade,
                "provisional": overall_provisional,
                "categories": cat_results,
            }

    def term_gpa(
        self,
        student_id: str,
        class_records: List[ClassRecord],
    ) -> Optional[float]:
        """Calculate a credit-weighted term GPA from this student's class grades.

        Uses the grade-point boundaries from Student.compute_gpa_from_courses:
          90–100 → 4.0,  80–<90 → 3.0,  70–<80 → 2.0,  60–<70 → 1.0,  <60 → 0.0

        Only classes with a non-null calculated grade contribute.
        Returns None if no class has a calculable grade.

        Note: separate from Student._gpa (manual cumulative GPA).
        """
        total_credits = 0.0
        weighted_gp = 0.0
        for cr in class_records:
            result = self.class_result(student_id, cr.id)
            g = result["grade"]
            if g is None:
                continue
            gp = _grade_to_points(g)
            total_credits += cr.credits
            weighted_gp += cr.credits * gp
        if total_credits == 0:
            return None
        return round(weighted_gp / total_credits, 2)

    # ══════════════════════════════════════════════════════════════════════════
    #  Serialization helpers (used by storage backends)
    # ══════════════════════════════════════════════════════════════════════════

    def categories_to_list(self) -> List[dict]:
        with self._lock:
            return [c.to_dict() for c in self._categories.values()]

    def enrollment_grades_to_list(self) -> List[dict]:
        with self._lock:
            return [eg.to_dict() for eg in self._enrollment_grades.values()]

    def load_from_data(
        self,
        categories: List[dict],
        enrollment_grades: List[dict],
    ) -> None:
        """Replace in-memory state from raw serialized data.

        Silently drops malformed entries.
        """
        new_cats: Dict[str, Category] = {}
        for raw in categories:
            try:
                cat = Category.from_dict(raw)
                new_cats[cat.id] = cat
            except (KeyError, ValueError):
                pass

        new_egs: Dict[Tuple[str, str], EnrollmentGrade] = {}
        for raw in enrollment_grades:
            try:
                eg = EnrollmentGrade.from_dict(raw)
                new_egs[(eg.student_id, eg.class_id)] = eg
            except (KeyError, ValueError):
                pass

        with self._lock:
            self._categories = new_cats
            self._enrollment_grades = new_egs

    # ══════════════════════════════════════════════════════════════════════════
    #  Internal helpers
    # ══════════════════════════════════════════════════════════════════════════

    def _find_possible(self, class_id: str, assignment_id: str) -> Optional[float]:
        """Returns the possible points for an assignment within a class, or None."""
        for cat in self._categories.values():
            if cat.class_id != class_id:
                continue
            asn = cat.get_assignment(assignment_id)
            if asn is not None:
                return asn.possible
        return None


# ── Module-level helper ───────────────────────────────────────────────────────

def _grade_to_points(grade: float) -> float:
    """Convert a 0–100 percentage grade to a 4.0-scale grade point."""
    if grade >= 90:
        return 4.0
    if grade >= 80:
        return 3.0
    if grade >= 70:
        return 2.0
    if grade >= 60:
        return 1.0
    return 0.0
