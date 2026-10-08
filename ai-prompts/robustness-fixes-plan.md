# Robustness Fixes Plan — app.js

## Overview

Four categories of defensive coding gaps in `app/static/js/app.js` cause crashes
or silent failures when the server returns unexpected responses or when an HTML
element is absent.  The fixes are surgical: add `res.ok` guards on every fetch,
guard `students[0]` access against an empty array, wrap all DOM-dependent
top-level code inside `DOMContentLoaded`, and add null checks before calling
`.addEventListener()` or reading properties on `getElementById` results.

No new features, no refactors beyond what is required by these four issues.

---

## Sub-Task 1 — Guard every `fetch` response with `res.ok`

**Intent**
A non-2xx HTTP response (e.g. 500) causes `res.json()` to decode the error body
and then silently discard the result, or throw an unhandled rejection, because
there is no check that the HTTP status was successful.  Every `fetch` call must
verify `res.ok` before calling `res.json()`.

**Expected Outcomes**
- Any server-side 4xx/5xx surfaced to the user via `showToast` with an
  informative error message.
- `res.json()` is never called on a non-OK response.

**Todo List**
1. In `loadStudents()` (~line 61): after `await fetch(...)`, throw or branch on
   `!res.ok` before calling `res.json()`.
2. In `loadStats()` (~line 140): same pattern.
3. In `performSearch()` (~line 310): same pattern; on failure hide the result
   container and clear the highlight.
4. In `sortStudents()` (~line 378): same pattern.
5. In `deleteStudent()` (~line 204): same pattern.
6. In the `editForm` submit handler (~line 269): same pattern.
7. In the `add-student-form` submit handler (~line 176): same pattern.

**Relevant Context**
- File: `app/static/js/app.js`
- The `catch` blocks already call `showToast` with `'error'` — the new `res.ok`
  branch should do the same, using `res.status` to form a helpful message such
  as `'Server error (${res.status}). Please try again.'`.

**Status** — `[x] done`

---

## Sub-Task 2 — Guard `students[0]` access against an empty array

**Intent**
In `performSearch()` the branch `if (data.found)` does not verify
`data.students.length > 0`.  If the server returns `{ found: true, students: [] }`
the code crashes on `students[0]`.

**Expected Outcomes**
- Accessing `students[0]` only happens when `students.length > 0` is confirmed.
- An empty `students` array with `found: true` is treated as "not found" from the
  UI perspective (hide result container, clear highlight).

**Todo List**
1. In `performSearch()` (~line 313), change the condition from
   `if (data.found)` to `if (data.found && data.students && data.students.length > 0)`.
2. The `else` branch (hiding the container and clearing the highlight) already
   handles the "not found" case — no additional code needed in that branch.

**Relevant Context**
- File: `app/static/js/app.js`, function `performSearch`, ~lines 313–333.

**Status** — `[x] done`

---

## Sub-Task 3 — Move all top-level DOM-dependent code inside `DOMContentLoaded`

**Intent**
All `document.getElementById(...)` calls and `.addEventListener(...)` calls at
the top level of `app.js` execute synchronously when the script is parsed, which
is before the DOM is fully available (even though the `<script>` tag sits at the
bottom of `<body>`, this is fragile and will break if the tag is ever moved, or
if an id is renamed).  The existing `DOMContentLoaded` callback at the bottom of
the file only wraps `loadStudents()`.  All DOM-touching initialisation should
move inside that callback.

This also ensures every `getElementById` result is the live element, not `null`.

**Expected Outcomes**
- The `DOMContentLoaded` handler contains all DOM queries and event listener
  registrations.
- The only code that executes at parse time is: `const API = {...}`, the pure
  helper functions (`showToast`, `getGradeStatus`, `getGradeColor`,
  `escapeHtml`, `renderStudentTable`, `loadStudents`, `loadStats`,
  `deleteStudent`, `openEditModal`, `closeEditModal`, `performSearch`,
  `highlightRow`, `clearHighlight`, `sortStudents`), and `let searchDebounce`.
- All `const editModal = ...`, `const editForm = ...`, etc. (lines 221–226)
  move inside `DOMContentLoaded`.
- All `.addEventListener(...)` calls that reference those consts move inside
  `DOMContentLoaded`.
- `const searchInput` and `const searchResultContainer` (lines 292–293) and
  their `addEventListener` move inside `DOMContentLoaded`.
- The sort button and save button `addEventListener` calls (lines 373–374, 391)
  move inside `DOMContentLoaded`.

**Todo List**
1. Identify every statement outside a function that touches the DOM (all
   `getElementById` assignments and `addEventListener` calls at top level).
2. Move them all into the existing `DOMContentLoaded` callback at the bottom of
   the file, keeping their relative order.
3. Update any functions that close over the moved constants (e.g.
   `openEditModal`, `closeEditModal`) to either accept parameters or reference
   the elements via `document.getElementById` internally — whichever is simpler.
4. Verify the `editModal.addEventListener('click', ...)` overlay-close handler
   and the global `keydown` Escape handler are also inside `DOMContentLoaded`.

**Relevant Context**
- File: `app/static/js/app.js`
- Top-level DOM code: lines 156, 221–226, 242–243, 246–255, 257, 292–293,
  295–306, 351, 364, 373–374, 391.
- `DOMContentLoaded` callback: lines 409–411.

**Status** — `[x] done`

---

## Sub-Task 4 — Add null checks before `.addEventListener()` and property access on `getElementById` results

**Intent**
Even after Sub-Task 3, if an HTML element is ever renamed or removed, the code
will throw a `TypeError: Cannot read properties of null`.  Adding explicit null
guards before each `.addEventListener()` and before each property access
(`textContent`, `classList`, etc.) on an `getElementById` result makes the
script resilient to template changes and easier to debug (the error becomes
visible rather than a cryptic crash).

**Expected Outcomes**
- Every call site that uses the result of `getElementById` checks for `null`
  before calling methods on it.
- A missing element logs a `console.warn` with the element id so developers can
  diagnose the mismatch quickly.
- No existing functionality changes for users when all elements are present.

**Todo List**
1. For each `getElementById` result used to call `.addEventListener()`, add a
   null guard: `if (!el) { console.warn('Missing element: <id>'); return; }`.
2. For `renderStudentTable`: guard `tbody` and `subtitle` at lines 71–72.
3. For `loadStats`: guard all five stat elements at lines 143–147 (can use a
   helper: `setTextIfExists(id, value)`).
4. For `performSearch`: guard `result-name`, `result-id`, `result-grade` before
   writing `textContent` on them (~lines 319–324).
5. For the `btn-search-locate` click handler: guard `result-name` before reading
   `.textContent` (~line 353).

**Relevant Context**
- File: `app/static/js/app.js`
- Pattern already used in the codebase: `highlightRow` at line 341 does `if (row) { ... }` — follow this style.

**Status** — `[x] done`

---

## Execution Order

Sub-tasks are independent enough to be applied sequentially in one pass, but
Sub-Task 3 (moving code into `DOMContentLoaded`) should be done **before**
Sub-Task 4 so that null-check guards are added to the already-relocated code,
keeping the diff readable.

Recommended order: **1 → 2 → 3 → 4**
