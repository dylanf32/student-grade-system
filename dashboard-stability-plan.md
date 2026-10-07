# Dashboard Stability & Efficiency Plan

## Overview

This plan addresses 17 identified issues across the student grade system — from production-blocking
security and concurrency bugs down to polish and test coverage gaps. Issues are grouped into four
focused sub-tasks ordered by risk. Each sub-task is designed to be implemented and reviewed
independently.

No architectural rewrites. Every change is the minimal fix that eliminates the identified risk.

---

## Sub-Task A — Security Fixes

**Status:** `[ ] pending`

### Intent
Eliminate the XSS vulnerability in the table renderer and protect the application from corrupted
JSON crashing on startup.

### Issues Covered
- **Issue 2 (HIGH)**: XSS via inline `onclick` handlers in `app.js` — `s.name` is embedded
  directly into `onclick="openEditModal(...)"` string, allowing a malicious student name to break
  out of the attribute and execute arbitrary JavaScript.
- **Issue 3 (HIGH)**: `Student.from_dict()` in `student.py` directly accesses `data["name"]` and
  `data["grade"]` without catching `KeyError`. Corrupted or manually-edited JSON will crash the
  entire application on load.

### Expected Outcomes
- Table row edit/delete buttons use `data-*` attributes and `addEventListener` instead of inline
  `onclick` strings. A student name containing quotes, apostrophes, or JS syntax renders safely.
- `Student.from_dict()` raises a clean `ValueError` (not `KeyError`) when required fields are
  missing, allowing callers to recover gracefully.

### Todo List
1. In `app.js` `renderStudentTable()`: replace inline `onclick` string-building with `dataset`
   attributes set via JS, and attach click handlers via `addEventListener`.
2. In `student.py` `from_dict()`: wrap `data["name"]` and `data["grade"]` access in a `try/except
   KeyError` block and re-raise as `ValueError` with a descriptive message.

### Relevant Context
- `app/static/js/app.js` — `renderStudentTable()` function, lines ~88–114
- `app/models/student.py` — `from_dict()` classmethod, line ~122

---

## Sub-Task B — Backend Thread Safety

**Status:** `[ ] pending`

### Intent
Prevent race conditions when multiple HTTP requests hit the Flask server concurrently. The global
`StudentManager` instance is shared across all routes with no synchronization.

### Issues Covered
- **Issue 1 (CRITICAL)**: `run_web.py` holds a single global `manager` object. Concurrent requests
  to mutating routes (`POST /api/students`, `PUT`, `DELETE`, `POST /api/sort`) operate on the same
  `_students` list simultaneously with no lock, risking list corruption or index errors.

### Expected Outcomes
- A `threading.Lock()` (or `threading.RLock()`) guards every route that reads or mutates
  `manager`. The lock is acquired before the operation and released after. No two requests can
  mutate state at the same time.
- Read-only routes (e.g. `GET /api/stats`, `GET /api/search`) are also covered since the list
  could be mutated mid-read.

### Todo List
1. In `run_web.py`: create a module-level `manager_lock = threading.RLock()`.
2. Wrap every route handler body in `with manager_lock:` before any access to `manager`.
3. Import `threading` at the top of `run_web.py`.

### Relevant Context
- `run_web.py` — global `manager` declaration (~line 17), all seven route handlers

---

## Sub-Task C — Frontend Hardening

**Status:** `[ ] pending`

### Intent
Prevent the frontend JavaScript from crashing when expected DOM elements are absent, when the
server returns an error HTTP status, or when an API response contains an empty array that is
immediately indexed.

### Issues Covered
- **Issue 4 (HIGH)**: `getElementById` called without null checks at `students-table-body`,
  `table-subtitle`, all six stats elements, all modal elements.
- **Issue 5 (HIGH)**: `addEventListener` called directly on `getElementById` results for
  `modal-close`, `btn-edit-cancel`, and search elements — crashes if element is missing.
- **Issue 6 (HIGH)**: `loadStudents()`, `loadStats()`, and `performSearch()` call `res.json()`
  without first checking `res.ok`. A 500 response silently disappears.
- **Issue 7 (HIGH)**: `performSearch()` accesses `students[0]` after checking `data.found` but not
  `students.length > 0`.
- **Issue 13 (LOW)**: Grade range `0`–`100` is hardcoded in `addStudent()` validation instead of
  sourced from configuration.
- **Issue 15 (LOW)**: Toast `setTimeout` does not cancel when a toast is manually removed,
  operating on a detached node.

### Expected Outcomes
- Every `getElementById` / `querySelector` result is checked for `null` before use; missing
  elements log a console warning and return early rather than throwing.
- All fetch calls check `res.ok` and call `showToast(...)` with the HTTP status on failure before
  returning.
- `performSearch()` guards `students[0]` with an array-length check.
- Grade range constants are defined once at the top of `app.js` (matching `config.py`) so a
  single edit keeps frontend and backend in sync.
- Toast `setTimeout` stores the timer ID and clears it on manual removal.

### Todo List
1. Add a helper `getEl(id)` in `app.js` that wraps `getElementById` with a null check and
   `console.warn`.
2. Replace all bare `getElementById` / `querySelector` calls with `getEl()` (or add inline null
   guards for event-listener setup).
3. After every `await fetch(...)`, add `if (!res.ok) { showToast(...); return; }` before
   `res.json()`.
4. In `performSearch()`: add `if (!students || students.length === 0)` guard before `students[0]`.
5. Extract `MIN_GRADE = 0` and `MAX_GRADE = 100` constants at the top of `app.js` and replace the
   hardcoded values in `addStudent()` validation.
6. In the toast system: store `setTimeout` return value on the element via `dataset.timerId` and
   clear it when the toast is removed manually.

### Relevant Context
- `app/static/js/app.js` — `renderStudentTable()`, `loadStudents()`, `loadStats()`,
  `performSearch()`, `openEditModal()`, `DOMContentLoaded` block

---

## Sub-Task D — Validation Consistency & Minor Logic Fixes

**Status:** `[ ] pending`

### Intent
Align the CLI and web validation rules, fix inconsistent error-handling patterns in the service
layer, and close small logic gaps.

### Issues Covered
- **Issue 8 (MEDIUM)**: `run_web.py` does inline name/grade validation that bypasses
  `InputValidator`. CLI enforces 2-char minimum and no-digit rule; web does not.
- **Issue 9 (MEDIUM)**: `run_web.py` lines ~54–55 coerce `85.0` → `85` (int) but leave `85.5` as
  float. The API grade type should be consistent (always float).
- **Issue 10 (MEDIUM)**: `handlers.py` sort choice only validates it is an integer, not that it is
  `1` or `2`. Values like `3` silently sort ascending.
- **Issue 11 (MEDIUM)**: `StudentManager.get_student()` returns `None` on invalid index, while
  `update_grade()` and `remove_student()` raise `ValueError`. Inconsistent contract.
- **Issue 12 (MEDIUM)**: `StatisticsService.get_highest()` and `get_lowest()` return `0` for an
  empty student list (via `default=0`). Should return `None` to distinguish "no students" from
  "lowest grade is 0".
- **Issue 14 (LOW)**: `InputValidator.validate_name()` rejects names containing any digit. This is
  undocumented, overly strict, and only enforced via CLI — not web.
- **Issue 17 (LOW)**: No test coverage for `Student.from_dict()` with malformed input (missing
  `name` or `grade` key). After Sub-Task A adds the `try/except`, a test should confirm the
  behavior.

### Expected Outcomes
- Web routes delegate name and grade validation to `InputValidator` instead of duplicating logic
  inline. CLI and web reject the same set of invalid inputs.
- Grade type in API responses is always `float` (e.g. `85.0` not `85`).
- Sort handler in `handlers.py` rejects any choice outside `{1, 2}` with a user-visible error.
- `get_student()` raises `ValueError` on out-of-range index (matching sibling methods), or is
  documented as `Optional[Student]` with all call sites updated.
- `get_highest()` / `get_lowest()` return `None` for empty list; callers and the stats API route
  handle `None` gracefully.
- No-digit name rule removed from `InputValidator` (or moved to CLI-only validation), with a
  comment explaining the decision.
- A test in `test_student.py` covers `from_dict()` with a dict missing `name` and missing `grade`.

### Todo List
1. In `run_web.py` `POST /api/students` and `PUT /api/students/<id>`: replace inline validation
   with calls to `InputValidator.validate_name()` and `InputValidator.validate_grade()`.
2. In `run_web.py`: remove the `int(grade_val)` coercion branch so grades are always returned as
   `float`.
3. In `handlers.py` `handle_sort_students()`: after `get_int()`, validate `choice in (1, 2)` and
   display an error and return if not.
4. In `student_manager.py` `get_student()`: raise `ValueError` on invalid index instead of
   returning `None`, OR declare return type as `Optional[Student]` and add null checks at all
   call sites.
5. In `statistics_service.py` `get_highest()` / `get_lowest()`: change `default=0` to
   `default=None`; update the stats route in `run_web.py` to handle `None` (send `null` in JSON).
6. In `input_validator.py`: remove or comment out the no-digit name rule with a note that it was
   inconsistent with the web layer.
7. In `tests/test_student.py`: add two test cases for `Student.from_dict()` with missing `name`
   and missing `grade` keys, asserting `ValueError` is raised.

### Relevant Context
- `run_web.py` — `POST /api/students` (~line 43), `PUT /api/students/<id>` (~line 70)
- `app/validators/input_validator.py` — `validate_name()`, `validate_grade()`
- `app/ui/handlers.py` — `handle_sort_students()` (~line 162)
- `app/services/student_manager.py` — `get_student()` (~line 80)
- `app/services/statistics_service.py` — `get_highest()`, `get_lowest()` (~lines 93, 98)
- `app/models/student.py` — `from_dict()` (~line 122)
- `tests/test_student.py`
