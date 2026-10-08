# Polish & Robustness Fixes Plan — Issues 13–17

## Overview

Five low-severity gaps in code quality, consistency, and test coverage. Each fix
is surgical: no new features, no structural refactors. The issues are grouped
into three natural buckets — frontend sync, name validation policy, and test
coverage — and implemented as independent sub-tasks.

---

## Sub-Task 1 — Expose grade bounds via API; consume in frontend (Issue 13)

**Intent**
`app/static/js/app.js` hardcodes `0` and `100` in two grade validation sites
(lines 202 and 432). If `MIN_GRADE` / `MAX_GRADE` in `app/config.py` ever
change, the frontend silently stays out of sync. Adding a `/api/config` endpoint
that returns the grade bounds, fetched once at startup, keeps the single source
of truth in `config.py`.

**Expected Outcomes**
- A new `GET /api/config` route in `run_web.py` returns
  `{ "min_grade": 0, "max_grade": 100 }` sourced directly from `config.MIN_GRADE`
  and `config.MAX_GRADE`.
- `app.js` fetches `/api/config` on `DOMContentLoaded` and stores the bounds in
  module-level variables `minGrade` / `maxGrade` (defaulting to `0` / `100` so
  the page is still usable if the fetch fails).
- The two hardcoded validation blocks (lines 202–203 and 432–433) replace
  the literal `0` / `100` with `minGrade` / `maxGrade`.
- The two toast messages update to read `between ${minGrade} and ${maxGrade}`.

**Todo List**
1. In `run_web.py`, import `MIN_GRADE` and `MAX_GRADE` from `app.config` and add
   a `GET /api/config` route that returns them as JSON.
2. In `app.js`, declare `let minGrade = 0; let maxGrade = 100;` near the top
   (after the `API` constant block).
3. Add an `async function loadConfig()` that fetches `/api/config` and assigns
   the returned values to `minGrade` / `maxGrade`; call it inside
   `DOMContentLoaded` before `loadStudents()`.
4. Replace both hardcoded `0` / `100` comparisons on lines 202 and 432 with
   `minGrade` / `maxGrade`, and update the accompanying toast strings.
5. Add `/api/config` to the `API` constant object so it follows the existing
   URL-management pattern.

**Relevant Context**
- `app/config.py` lines 11–12: `MIN_GRADE = 0`, `MAX_GRADE = 100`
- `app/static/js/app.js` line 202: `Number(grade) < 0 || Number(grade) > 100`
- `app/static/js/app.js` line 432: `Number(newGrade) < 0 || Number(newGrade) > 100`
- `run_web.py`: all other routes follow the `@app.route / jsonify` pattern

**Status** — `[x] done`

---

## Sub-Task 2 — Relax name validation to allow digits (Issue 14)

**Intent**
`input_validator.py` line 32 rejects any name containing a digit, which blocks
culturally valid names like "John 2nd" or names with ordinal suffixes. This only
affects the CLI path; the web API relies on the `Student` model constructor which
has no such restriction. The rule should be removed; the existing non-empty and
minimum-length checks are sufficient.

**Expected Outcomes**
- `InputValidator.validate_name()` no longer rejects names containing digits.
- Names like "John 2nd" and "O'Brien Jr2" pass validation.
- All existing `test_input_validator.py` tests still pass (the digit-rejection
  test, if one exists, is updated or removed).

**Todo List**
1. In `app/validators/input_validator.py`, remove lines 32–33 (the
   `any(ch.isdigit() ...)` check and its return statement).
2. Locate and update `tests/test_input_validator.py` (if it exists): remove or
   rewrite the test that asserts a digit-containing name is rejected; add a test
   confirming "John 2nd" is now accepted.

**Relevant Context**
- `app/validators/input_validator.py` lines 28–34: full `validate_name` body
- Only the CLI layer calls `InputValidator.validate_name()`; the web API does not
  (the `Student` constructor validates name emptiness independently)

**Status** — `[x] done`

---

## Sub-Task 3 — Cancel the toast timeout on manual removal (Issue 15)

**Intent**
`app.js` line 32 schedules toast removal with `setTimeout`. The `if (toast.parentNode)`
guard prevents a crash when the toast is removed before the timeout fires, but
the timeout itself is never cancelled. If a toast is manually dismissed, the
dangling timeout fires later and attempts a no-op removal. The fix is to store
the timer ID and clear it on manual removal, making the lifecycle explicit.

**Expected Outcomes**
- The `setTimeout` return value is stored.
- If a toast is dismissed before the timeout (e.g. clicked away or replaced),
  `clearTimeout` is called so no dangling callback remains.
- The existing `if (toast.parentNode)` guard is retained as a belt-and-suspenders
  safety net.
- Visual behaviour (5-second auto-dismiss) is unchanged.

**Todo List**
1. In `showToast()` in `app.js`, capture the `setTimeout` return value:
   `const timerId = setTimeout(...)`.
2. Attach the ID to the toast element: `toast.dataset.timerId = timerId`.
3. When the toast is removed (either by the timeout itself or any external
   removal), call `clearTimeout(toast.dataset.timerId)` before removing the node.
   Because the only current removal path is the timeout itself, the simplest
   implementation is to call `clearTimeout(timerId)` at the top of the timeout
   callback (a no-op if it already fired) — this is the minimal change that
   eliminates the dangling-timer concern without adding a separate dismiss button.

**Relevant Context**
- `app/static/js/app.js` lines 31–34: the `setTimeout` block inside `showToast`
- No other code currently removes toasts; the fix is entirely local to
  `showToast()`

**Status** — `[x] done`

---

## Sub-Task 4 — Add `__repr__` test (Issue 16)

**Intent**
`test_student.py` has a `test_str` test (line 84) that covers `__str__` but no
equivalent test for `__repr__`. The `__repr__` method at `student.py` lines
142–143 returns `Student(name='...', grade=..., id='...')` and is a real public
interface (used in REPL and debug output). Adding one focused test closes the
gap.

**Expected Outcomes**
- A new `test_repr` test in `TestStudentSerialization` asserts that `repr(s)`
  contains the student name, grade, and id.
- `__repr__` is now covered in the test suite.

**Todo List**
1. In `tests/test_student.py`, inside `TestStudentSerialization`, add:
   ```python
   def test_repr(self):
       s = Student("Ali", 80)
       r = repr(s)
       self.assertIn("Ali", r)
       self.assertIn("80", r)
       self.assertIn(s.id, r)
   ```

**Relevant Context**
- `app/models/student.py` lines 142–143: `__repr__` implementation
- `tests/test_student.py` lines 84–87: existing `test_str` to mirror

**Status** — `[x] done`

---

## Sub-Task 5 — Add `from_dict()` malformed-input tests (Issue 17)

**Intent**
`Student.from_dict()` raises `ValueError` when `name` or `grade` is missing from
the input dict (lines 124–130 of `student.py`), but no test exercises this path.
The error-handling code is untested, so a regression (e.g. swallowing the
exception) would go undetected.

**Expected Outcomes**
- A new `TestStudentFromDictMalformed` class in `test_student.py` contains tests
  that confirm `ValueError` is raised for:
  1. A dict missing the `name` key.
  2. A dict missing the `grade` key.
  3. `None` passed instead of a dict (the `TypeError` path in the `except`
     clause, re-raised as `ValueError`).

**Todo List**
1. In `tests/test_student.py`, add a new test class after `TestStudentSerialization`:
   ```python
   class TestStudentFromDictMalformed(unittest.TestCase):
       def test_missing_name_raises(self):
           with self.assertRaises(ValueError):
               Student.from_dict({"grade": 50})

       def test_missing_grade_raises(self):
           with self.assertRaises(ValueError):
               Student.from_dict({"name": "Ali"})

       def test_none_input_raises(self):
           with self.assertRaises(ValueError):
               Student.from_dict(None)
   ```

**Relevant Context**
- `app/models/student.py` lines 107–130: `from_dict` with `try/except (KeyError, TypeError)`
- `tests/test_student.py` lines 64–88: existing `TestStudentSerialization` to
  place the new class after

**Status** — `[x] done`

---

## Execution Order

Sub-tasks are fully independent. Recommended order by risk/impact:

**5 → 4 → 2 → 3 → 1**

- Start with pure test additions (5, 4) — zero risk, immediate coverage gain.
- Then fix the name validation policy (2) — small one-line backend change.
- Then the toast cleanup (3) — small, self-contained JS change.
- Finally the API + frontend grade-bounds sync (1) — requires both a new backend
  route and coordinated JS changes.
