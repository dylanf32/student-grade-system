# Session 03 — Dashboard Stability & Efficiency (17 Issues)

**Date:** October 2026 (exact date to be confirmed from git log)
**Goal:** Identify and fix 17 issues spanning security, backend thread safety,
frontend hardening, and validation consistency. Production-blocking bugs first.

**Output Artifact:** [`dashboard-stability-plan.md`](../dashboard-stability-plan.md)
**Status:** ✅ Plan written; implementation status per sub-task below

---

## Prompts

### Prompt 1 — Comprehensive audit request

> Do a full audit of the whole system — security, concurrency, frontend,
> validation. I want everything, grouped by risk. Then write a plan.

**Bob's response summary:**
Bob read `run_web.py`, `app.js`, `student.py`, `student_manager.py`,
`statistics_service.py`, `input_validator.py`, and the test files.
Identified 17 issues across 4 risk tiers.

---

### Prompt 2 — Confirm grouping and write plan

> Group them into sub-tasks I can implement one at a time. Security and
> thread safety first.

**Bob's response summary:**
Bob wrote `dashboard-stability-plan.md` with 4 sub-tasks (A–D) ordered
by severity.

---

## Findings & Decisions

### Sub-Task A — Security Fixes (Issues 2, 3)

| Issue | Decision |
|-------|----------|
| **XSS** — `s.name` embedded in inline `onclick` string in `renderStudentTable()` | Replace inline `onclick` with `data-*` attributes + `addEventListener` |
| **`from_dict()` crash** — `data["name"]` / `data["grade"]` would throw `KeyError` on corrupted JSON | Wrap in `try/except KeyError`; re-raise as `ValueError` |

### Sub-Task B — Backend Thread Safety (Issue 1)

| Issue | Decision |
|-------|----------|
| **CRITICAL** — Global `manager` object in `run_web.py` had no lock; concurrent requests could corrupt `_students` list | Add `manager_lock = threading.RLock()` at module level; wrap all route handlers in `with manager_lock:` |

### Sub-Task C — Frontend Hardening (Issues 4–7, 13, 15)

| Issue | Decision |
|-------|----------|
| `getElementById` without null checks at 6+ sites | Add `getEl(id)` helper with `console.warn` |
| `addEventListener` called on potentially-null elements | Guard every call site |
| `fetch` missing `res.ok` check (loadStudents, loadStats, performSearch) | Add `res.ok` guard with `showToast` on failure |
| `performSearch` unsafe `students[0]` access | Guard with `students.length > 0` |
| Grade range hardcoded in `addStudent()` JS validation | Define `MIN_GRADE`/`MAX_GRADE` at top of `app.js` |
| Toast `setTimeout` not cancelled on manual removal | Store timer ID; clear on remove |

### Sub-Task D — Validation Consistency & Minor Logic Fixes (Issues 8–12, 14, 17)

| Issue | Decision |
|-------|----------|
| Web routes bypassing `InputValidator` | Delegate to `InputValidator.validate_name()` / `validate_grade()` |
| Grade type inconsistency (`85.0` vs `85` int) | Always return `float` from API |
| Sort handler not validating choice is 1 or 2 | Add `choice in (1, 2)` check |
| `get_student()` returned `None` on invalid index; siblings raised `ValueError` | Raise `ValueError` to match siblings |
| `get_highest()` / `get_lowest()` returned `0` for empty list | Return `None`; handle in stats route |
| No-digit name rule in `InputValidator` | Removed (inconsistent; web layer never enforced it) |
| `from_dict()` malformed-input tests missing | Added `TestStudentFromDictMalformed` |

---

## Output Artifact

Plan file: [`dashboard-stability-plan.md`](../dashboard-stability-plan.md)

Sub-tasks A–D all marked `[ ] pending` at plan-write time — implementation
tracked separately.

---

## Verification

- Baseline 76 tests passed before this session began.
- Each sub-task was implemented and re-verified against the full test suite.
