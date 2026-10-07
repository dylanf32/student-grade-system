# GradePulse — Improvements Made During the Hackathon

This file records the baseline state of the application and the specific improvements made during
the Building with IBM Bob hackathon event (September 28 – October 18, 2026).

---

## Baseline (before hackathon improvements)

- Working Flask web dashboard with CRUD, search, filter, sorting, CSV import/export, and statistics.
- Console UI with menu-driven workflow.
- 138 unit tests passing (model, service, storage, validation).
- Known gaps (documented in HACKATHON_PLAN.md):
  - Grade threshold hardcoded in three separate places with no shared constant.
  - Frontend labeled passing grades 60–69 as "Below Avg" — misleading.
  - Add/update/delete APIs reported success even when `save()` returned `False`.
  - No per-student support flags or explainable at-risk dashboard.
  - No grade-distribution visualization.
  - No full-featured synthetic demo data.

---

## Improvements made during the event

### 1. Unified grade threshold policy

**Files changed:** `app/config.py`, `app/services/statistics_service.py`, `run_web.py`, `app/static/js/app.js`

- Added `PASSING_THRESHOLD: int = 60` to `app/config.py` as the single source of truth.
- `StatisticsService` now imports `PASSING_THRESHOLD` instead of hardcoding `60`.
- `/api/config` now returns `passing_threshold` so the frontend stays in sync automatically.
- Frontend grade badge for 60–69 changed from `"Below Avg"` to `"Passing (D)"` — accurately
  reflects that these students are passing.

### 2. Accurate save-failure reporting with rollback

**Files changed:** `run_web.py`

- Add, update, delete, and sort routes now check `manager.save()` return value.
- On save failure: the in-memory mutation is rolled back before returning HTTP 500.
  - Add: removes the just-added student.
  - Update: restores the previous field values.
  - Delete: re-inserts the student at its original index.
- Sort: reports failure with a warning; in-memory order is retained but the client is informed
  the order was not persisted.

### 3. InsightsService, /api/insights, and Support Panel

**Files changed / created:** `app/services/insights_service.py` (new), `run_web.py`, `app/templates/index.html`, `app/static/js/app.js`, `tests/test_insights.py` (new)

- New stateless `InsightsService` derives one flag per student: `needs_attention` if grade is
  below `PASSING_THRESHOLD`, `passing` otherwise. Each flag carries a factual reason string.
- New `GET /api/insights` endpoint returns the full flag list.
- Dashboard shows a Support Panel between the stats grid and the student table.
  - Panel is hidden when no students are flagged.
  - Updates automatically when grades change (called alongside `loadStudents`).
- 9 new unit tests verify empty roster, flag logic, boundary cases, reason text, ordering,
  and ID/name preservation.

### 4. Grade-distribution chart (no new dependencies)

**Files changed:** `run_web.py`, `app/templates/index.html`, `app/static/js/app.js`

- `/api/stats` now includes `grade_distribution` from `StatisticsService.compute_analytics()`.
- Dashboard renders a horizontal bar chart using vanilla SVG (`document.createElementNS`).
  Five grade bands (A through F) are shown with proportional color-coded bars and per-band counts.
- No new JavaScript libraries, CDN links, or build steps were added.

### 5. Synthetic demo roster

**Files created:** `data/demo_students.json`

- 18 synthetic students using the full supported schema (`id`, `name`, `grade`, `email`, `major`,
  `academic_year`, `gpa`, `courses`, `notes`).
- Grade distribution spans all five bands (A, B, C, D, F).
- 4 students are intentionally below the passing threshold to demonstrate the Support Panel.
- `data/students.json` (original data) was not modified.

---

## Test results

| State | Result |
|---|---|
| Baseline | 138 tests, all passing |
| After all improvements | 147 tests, all passing (+9 InsightsService tests) |

---

## What was not changed

- Architecture, module boundaries, and existing behavior outside the five improvements above.
- Console UI (`main.py`, `app/ui/`).
- Storage backend (`JsonStorage`, `BaseStorage`).
- CSV import/export.
- All existing passing tests — no regressions.
