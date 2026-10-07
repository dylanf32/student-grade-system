# Code Audit Fixes Plan

Addresses every confirmed issue from the October 2026 audit, ordered
critical-first.  Each sub-task is self-contained and safe to
implement independently.

---

## Top-Level Overview

**Goal:** Fix all confirmed code bugs and type-annotation mismatches,
add missing test coverage, create an `ai-prompts/` folder tracking
every AI conversation used during this project, and update the README
to correctly credit the original author while positioning this as a
hackathon fork.

**Scope:**
- A1 — thread-safety bug in `get_student()`
- A2 — `sort_by_grade()` leaks internal list reference
- A3 — `InputHelper.get_grade()` hardcodes grade bounds
- B1 — `grade: int` annotation on float params in `StudentManager`
- B2 — `_grade_badge(grade: int)` wrong annotation in `Display`
- C1 — `get_student()` has no direct test
- C2 — `is_empty()` has no direct test
- C3 — `search_all_by_name()` missing from `test_student_manager.py`
- README — attribution and hackathon framing
- ai-prompts/ — new folder + initial log of all prior conversations

**Not in scope:** D1 (unused variable), D2 (dead method) — omitted per
user request.

---

## Sub-Tasks

---

### ST-1 — Fix `get_student()` missing lock  [A1]

**Intent**
`get_student()` reads `self._students[index]` without holding
`self._lock`. Every other mutating and reading method acquires the
lock, so this is an inconsistency that can cause a race condition under
concurrent use (e.g., the Flask server).

**Expected Outcomes**
- `get_student()` acquires `self._lock` before reading the list.
- Existing tests still pass.

**Todo List**
1. In `app/services/student_manager.py`, wrap the body of
   `get_student()` in a `with self._lock:` block (mirror the pattern
   used by `get_all_students()`).

**Relevant Context**
- File: `app/services/student_manager.py`, lines 72–87
- Pattern to mirror: `get_all_students()` lines 89–96

**Status:** [ ] pending

---

### ST-2 — Fix `sort_by_grade()` leaking internal list reference  [A2]

**Intent**
`sort_by_grade()` currently returns `self._students` directly.  Any
caller that stores this reference can mutate internal state without
going through the lock.  The fix is to return a shallow copy, matching
the contract of `get_all_students()`.

**Expected Outcomes**
- `sort_by_grade()` returns `list(self._students)`, not the original.
- Callers in `run_web.py` and `handlers.py` are unaffected because they
  only iterate the result, never mutate it.
- Existing sort tests still pass.

**Todo List**
1. In `app/services/student_manager.py` `sort_by_grade()`, change the
   return statement from `return self._students` to
   `return list(self._students)`.

**Relevant Context**
- File: `app/services/student_manager.py`, lines 198–212
- `get_all_students()` (lines 89–96) is the established pattern.

**Status:** [ ] pending

---

### ST-3 — `InputHelper.get_grade()` must use config constants  [A3]

**Intent**
`input_helpers.py` hardcodes `0` and `100` as grade bounds.  If
`MIN_GRADE`/`MAX_GRADE` in `config.py` are ever changed, the input
helper silently accepts the old range while the validator and model
reject it.  Importing the constants removes the discrepancy.

**Expected Outcomes**
- `get_grade()` validates `value < MIN_GRADE or value > MAX_GRADE`
  instead of `value < 0 or value > 100`.
- The error message says "between {MIN_GRADE} and {MAX_GRADE}."

**Todo List**
1. Add `from app.config import MIN_GRADE, MAX_GRADE` to
   `app/ui/input_helpers.py`.
2. Replace the hard-coded bounds check and its error string with the
   config constants.

**Relevant Context**
- File: `app/ui/input_helpers.py`, lines 64–69
- Config: `app/config.py` — `MIN_GRADE = 0`, `MAX_GRADE = 100`

**Status:** [ ] pending

---

### ST-4 — Fix `grade: int` type annotations in `StudentManager`  [B1]

**Intent**
`add_student()` and `update_grade()` declare `grade: int` and
`new_grade: int` but the entire system supports and stores `float`.
Regression tests already pass decimal values through these methods.
Correcting the annotations makes the API honest and removes misleading
IDE feedback.

**Expected Outcomes**
- Both method signatures use `float` for the grade parameter.
- No runtime behavior changes; all tests pass unchanged.

**Todo List**
1. In `app/services/student_manager.py`, change `add_student`
   signature from `grade: int` to `grade: float`.
2. Change `update_grade` signature from `new_grade: int` to
   `new_grade: float`.

**Relevant Context**
- File: `app/services/student_manager.py`, lines 42 and 102

**Status:** [ ] pending

---

### ST-5 — Fix `_grade_badge(grade: int)` type annotation  [B2]

**Intent**
`Display._grade_badge()` is annotated `grade: int` but receives
`float` grades throughout the codebase (decimal grades are a confirmed
feature).  Fix the annotation to `float`.

**Expected Outcomes**
- Method signature reads `grade: float`.
- `_grade_status()` (which delegates to `_grade_badge`) picks up the
  same change automatically.

**Todo List**
1. In `app/ui/display.py`, change `_grade_badge(grade: int)` to
   `_grade_badge(grade: float)`.

**Relevant Context**
- File: `app/ui/display.py`, line 286

**Status:** [ ] pending

---

### ST-6 — Add missing tests: `get_student()`, `is_empty()`, `search_all_by_name()`  [C1 C2 C3]

**Intent**
Three behaviors have no (or no direct) coverage in
`test_student_manager.py`:
- `get_student()` — valid index returns the right student; invalid
  index raises `ValueError`.
- `is_empty()` — returns `True` on a fresh manager, `False` after
  adding a student.
- `search_all_by_name()` — returns all case-insensitive matches as
  `(index, student)` tuples; returns `[]` for no match.

These are bundled into one sub-task because they all live in the same
test file.

**Expected Outcomes**
- `TestGetStudent`, `TestIsEmpty`, and `TestSearchAllByName` classes
  added to `tests/test_student_manager.py`.
- All new tests pass alongside the existing 76.

**Todo List**
1. Add `class TestGetStudent` with:
   - `test_get_valid_index` — add a student, assert `get_student(0)`
     returns it.
   - `test_get_invalid_index_raises` — assert `get_student(5)` raises
     `ValueError` on a 1-student list.
2. Add `class TestIsEmpty` with:
   - `test_empty_on_fresh_manager` — assert `is_empty()` is `True`.
   - `test_not_empty_after_add` — add a student, assert `is_empty()`
     is `False`.
3. Add `class TestSearchAllByName` with:
   - `test_single_match` — one student named "Ali"; `search_all_by_name("Ali")`
     returns one tuple.
   - `test_multiple_matches` — two students named "Ali"; returns two
     tuples.
   - `test_case_insensitive` — query "aLi" matches "Ali".
   - `test_no_match_returns_empty` — query "Zain" returns `[]`.

**Relevant Context**
- File: `tests/test_student_manager.py`
- Existing pattern: `TestSearchStudent` class at line 96

**Status:** [ ] pending

---

### ST-7 — Create `ai-prompts/` folder with all session logs  [NEW]

**Intent**
The hackathon requires evidence of IBM Bob usage.  A dedicated folder
captures every prompt used in this project across **all sessions** so
the submission work-log has traceable, dated entries.  Four sessions
have occurred so far; each gets its own file.

**Expected Outcomes**
- `ai-prompts/` folder exists at the repo root.
- `ai-prompts/README.md` explains the folder's purpose and format.
- One file per Bob session, reconstructed from the plan files that
  were produced in each session:
  - `session-01-app-js-robustness.md` — `robustness-fixes-plan.md`
  - `session-02-polish-robustness.md` — `polish-robustness-plan.md`
  - `session-03-dashboard-stability.md` — `dashboard-stability-plan.md`
  - `session-04-code-audit-and-fixes.md` — this session

**Todo List**
1. Create `ai-prompts/README.md` — purpose, format, one entry per
   session, to be linked from `submission/bob-work-log.md`.
2. Create `ai-prompts/session-01-app-js-robustness.md` — reconstructed
   from `robustness-fixes-plan.md` (4 sub-tasks, all marked done).
3. Create `ai-prompts/session-02-polish-robustness.md` — reconstructed
   from `polish-robustness-plan.md` (5 sub-tasks, all marked done).
4. Create `ai-prompts/session-03-dashboard-stability.md` — reconstructed
   from `dashboard-stability-plan.md` (Sub-Tasks A–D).
5. Create `ai-prompts/session-04-code-audit-and-fixes.md` — this
   session's prompts, findings (Groups A–D), and decisions.

**Relevant Context**
- Source plans: `robustness-fixes-plan.md`, `polish-robustness-plan.md`,
  `dashboard-stability-plan.md`, `code-audit-fixes-plan.md`
- `HACKATHON_PLAN.md` specifies a `submission/bob-work-log.md` — these
  files feed directly into that artifact.

**Status:** [ ] pending

---

### ST-8 — Update README: attribution and hackathon framing  [NEW]

**Intent**
The current README presents the project as an original creation with
no mention of the original author, the hackathon, or this fork's
purpose.  For the hackathon submission it must be clear that:
1. The original project was authored by the original creator.
2. This fork was built and extended by `ferreirav` for the IBM Bob
   Hackathon.

**Expected Outcomes**
- A "Credits & Attribution" section added to `README.md` crediting
  the original author with a GitHub link placeholder.
- A hackathon badge/banner at the top that links to the event.
- The existing content (architecture, features, test coverage) is
  preserved unchanged.

**Todo List**
1. Add an IBM Bob Hackathon badge to the badge row at the top of
   `README.md`.
2. Add a `## 🏆 Hackathon` section immediately after the badges
   stating: "Built by [@ferreirav](https://github.com/ferreirav) for
   the [IBM Bob Hackathon](https://hackathon.angelhack.com/web/events/building-with-ibm-bob).
   Forked and extended from
   [@the-original-author](https://github.com/the-original-author)'s
   student-grade-system."
3. Add a `## 🙏 Credits` section at the bottom of the README (before
   License) with the same attribution in long form.

**Relevant Context**
- File: `README.md`
- The placeholder `the-original-author` in both the badge URL and
  credits text **must be replaced with the real GitHub handle before
  submission** — leave as-is during implementation.
- `LICENSE` is already under the name "Samin" — do not modify LICENSE.

**Status:** [ ] pending

---

## Execution Order

```
ST-1 → ST-2 → ST-3   (bugs — no test changes needed)
ST-4 → ST-5           (annotations — purely cosmetic)
ST-6                   (tests — validates all of ST-1 through ST-5)
ST-7 → ST-8           (docs — independent of code fixes)
```

After ST-6 the full test suite must still show 76+ passing tests
with 0 failures before ST-7/ST-8 are started.
