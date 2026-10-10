# IBM Bob: fixes and additions

Prepared instructions, not implemented features. Keep this file in Bob's project.

**Start:** `Read the operating rules and first unfinished task in IBM_BOB_NEXT_STEPS.md. Complete that task only.`
**Continue:** `Continue with the next unfinished task in IBM_BOB_NEXT_STEPS.md. Follow its operating rules.`

**Operating rules — apply to both sections**
- Minimize Bobcoin use: read this file once per session; on continuation read only the task and progress. Check git status and applicable repository instructions. Inspect listed files and direct dependencies only; widen inspection only to resolve a specific blocker.
- Implement one task per turn. Skip tasks already verified. Reuse existing code/UI; preserve local changes, attribution, JSON data, student UUIDs, and console behavior. No broad audits, rewrites, unrelated upgrades, or speculative features.
- Run focused checks once after the change; rerun only after failures or further edits. Run the full suite at F2, A4, A6, and A12 checkpoints. Use temporary test data; workspace-local temp files if sandbox restrictions interfere.
- Keep output to 4 bullets: changed files, actual checks/results, limitation, next task. No source dumps or repeated plans. Update one compact progress table below, not a growing session narrative. Stop after the task. Do not commit, push, deploy, or claim unverified results.

## 1. Fixes

### F1 — Truthful save failures
**Read:** run_web.py; app/services/student_manager.py; app/storage/base_storage.py; app/storage/json_storage.py; relevant tests. Read app/static/js/app.js only for failure display.
CRUD currently ignores save=False. Make add/update/delete and sort return JSON success=false with HTTP 503 when saving fails; preserve prior memory and disk state. Guard mutation, persistence, and rollback together so concurrent changes cannot be erased. Preserve atomic JSON replacement. Explicit save must also return an appropriate failure status. Show useful errors as text. Test failed CRUD plus a successful save using injected storage and temporary data.

### F2 — Validate before changing records
**Read:** run_web.py; app/models/student.py; app/validators/input_validator.py; app/services/student_manager.py; relevant tests.
Current API accepts GPA 8 and boolean grades; malformed names/course grades can produce HTTP 500. Require JSON objects, string text fields, and a list of course objects with nonempty names. Grades: finite 0–100; GPA: finite 0–4; reject booleans before conversion. Preserve supported numeric strings. Course grade may be null; required overall grade may not. Reuse validation across construction, setters, and loading. Validate every supplied update field before applying any. Return useful JSON 400 for bad input, preserve standard 415 for unsupported content type, and leave state unchanged. Test the reported cases, invalid later update fields, and a valid decimal/course round trip. Run the full suite.

## 2. Additions

Follow this order; each numbered task is one Bob turn. Build shared data/calculations before UI to avoid rework.

### A1 — Classes and enrollments
**Read:** app/models/student.py; app/services/student_manager.py; storage interface/JSON implementation; app/config.py.
Add shared classes (UUID, code, title, term dates, positive credits) and student/class enrollments. Prevent duplicates/dangling references; reject deleting classes with dependents. Extend the storage contract minimally for the complete dataset. Version JSON and load legacy records without losing UUIDs, overall grades, notes, or courses. Do not merge legacy courses by name automatically. Back up before explicit migration. Test legacy loading and complete new-format round trip.

### A2 — Assignments and weighted grades
**Read:** A1 models/services and relevant tests.
Add per-class categories (finite nonnegative weights totaling 100%), assignments (positive possible points), and per-enrollment scores (null or finite 0–possible points; reject booleans). Category grade = total earned/possible for scored assignments. Class grade = weighted category average, renormalized over positive-weight categories with scored work. No effective graded weight = null. Return scored-work/category coverage; any ungraded work makes the result provisional. Zero is graded, null is ungraded. Round for display only. Keep legacy overall grades separate. Calculated term GPA uses existing grade-point boundaries, credit weighting, and is separate from manual cumulative GPA. Test unequal weights/points, zero/null, empty/zero-weight categories, invalid inputs, and one student with different grades in two classes.

### A3 — PostgreSQL storage
**Read:** revised storage/service interfaces; app/config.py; requirements.txt.
Add a PostgreSQL driver only if needed, parameterized SQL, foreign keys, transactions, and an explicit schema setup command. PostgreSQL is authoritative: do not overwrite newer database state from a stale process-wide roster or replace the whole database on each save. Keep JSON selectable. Failed writes roll back completely. Read DATABASE_URL from the environment; never log or commit secrets. Test failure handling with mocks; run disposable-database integration checks if available, otherwise report them unverified.

### A4 — Explicit JSON import
**Read:** A3 storage/schema and A1 serialization.
Provide a backup-first JSON-to-PostgreSQL import command, transactional with explicit UUID collision handling and verified entity counts. No automatic import on startup/connect; no destructive replacement. Preserve relationships and legacy fields. Test round trip and failed-import rollback. Run the full suite.

### A5 — PostgreSQL connection input
**Read:** run_web.py; app/config.py; A3 backend; existing dashboard HTML/JS/CSS.
Add connection settings with a masked PostgreSQL URL input, read-only Test connection, and explicit Connect. Test must not create schemas, migrate data, or switch backend. Failed connection keeps the previous backend. Never return/log/store credentials in browser storage, URL query strings, or committed files. Form credentials stay server-side in memory; use environment config across restarts. Use PostgreSQL-only parameters and bounded timeouts. Enable configuration only in an explicitly loopback-bound local-demo mode; disable its routes/UI on external binding. No arbitrary SQL input. Test failed connection and secret-free responses.

### A6 — Class selector and enrollment UI
**Read:** run_web.py; dashboard HTML/JS/CSS; A1 services.
Add class creation/editing, class selection, and enrollment controls. Keep all-students view. Scope API/views by class UUID. Prevent stale responses on class switching and silent loss of unsaved edits. Test two classes sharing a student and persistence after reload. Run the full suite.

### A7 — Gradebook UI
**Read:** A2 services; A6 routes/UI.
Add category/assignment editing and per-student score input, showing each class's calculated grades and provisional coverage. Validate weights as a complete configuration; prevent partial invalid changes. Reuse A2 calculations. Test score editing, null/zero, reload, and class isolation.

### A8 — Schedule data and conflicts
**Read:** A1 models/services/storage; app/config.py.
Add multiple weekly meetings per class: weekday, start/end time, location. Use one explicit timezone per term, default America/New_York; validate it. Start must precede end; no overnight meetings. Warn on enrollment meeting overlaps, allow intentional conflicts; adjacent meetings are valid. Respect term date overlap. Test overlapping/adjacent meetings, disjoint terms, and multiple meetings. Persist schedules in both backends.

### A9 — Weekly schedule UI
**Read:** A8 services; routes/dashboard files.
Add meeting editor and selected-student weekly schedule from enrollments, with conflict warnings and timezone label. Verify save/reload and exclusion of unenrolled classes. No calendar integration or exam exceptions.

### A10 — N1 support panel
**Read:** app/services/statistics_service.py; A2 grade service; run_web.py; dashboard files.
Add read-only InsightsService and class-scoped /api/insights. Flag grades below 60 with student/class/grade/reason and a simple action such as tutoring. Show incomplete/ungraded work separately; label provisional grades. Reuse calculations and configured thresholds. No AI API or prediction claims. Test empty class, 60 boundary, null/provisional grades, and class isolation.

### A11 — N2 grade chart
**Read:** statistics service; A2 calculations; routes/dashboard files.
Add accessible HTML/CSS or SVG bars with counts for <60, 60–<70, 70–<80, 80–<90, 90–100; ungraded separate, provisional labeled. Use selected-class data and shared thresholds. Refresh after edits/class switching. No chart dependency. Test fractional boundaries, empty state, and roster totals.

### A12 — Final verification and README
**Read:** changed features, relevant tests, README.md, requirements.txt.
Run the full suite once. Exercise two classes, weighted scores, schedule, support panel, and chart together; check PostgreSQL persistence if a test server exists. Update README with implemented setup, connection/schema/import commands, grade rules, and known limits. Report unavailable browser/database checks honestly. No deployment or fabricated Bob history.

**Progress — Bob updates only tasks actually attempted**

| Task | Status | Changed paths | Check/result or blocker |
| --- | --- | --- | --- |
| F1 | Done | run_web.py, app/services/student_manager.py, tests/test_f1_save_failures.py | 12/12 tests pass; all CRUD/sort/save return 503 on failure with rollback; delete rollback uses new `insert_student_at` instead of direct `_students` access |
| F2 | Done | app/validators/input_validator.py, run_web.py, tests/test_f2_validation.py | 237/237 full suite passes; booleans rejected before float(); course grades validated 0–100; all update fields validated before any apply; text fields require strings; 415 preserved |
| A1 | Done | app/models/class_record.py (new), app/services/class_manager.py (new), app/storage/base_storage.py, app/storage/json_storage.py, tests/test_a1_classes.py (new) | 279/279 full suite passes (42 new A1 tests); ClassRecord validates UUID/code/title/credits/dates; ClassManager guards duplicates, dangling refs, delete-with-dependents; JsonStorage v1↔v2 transparent load/save; legacy student UUIDs/grades/notes/courses preserved |
| A2 | Done | app/models/gradebook.py (new), app/services/gradebook_service.py (new), app/storage/base_storage.py, app/storage/json_storage.py, tests/test_a2_gradebook.py (new), tests/test_a1_classes.py | 331/331 full suite passes (52 new A2 tests); Category/Assignment/EnrollmentGrade validated; category grade = earned/possible over scored; class grade renormalized over categories with scored work; provisional if any positive-weight assignment ungraded; term GPA credit-weighted; JsonStorage bumped to v3 (v1/v2 load transparently) |
| A3 | Done | app/storage/postgres_storage.py (new), requirements.txt, tests/test_a3_postgres.py (new) | 360/360 full suite passes (29 new A3 tests); upsert-based save/save_dataset (PostgreSQL authoritative, no stale overwrite); all mutations transactional with full rollback on failure; setup_schema() creates 6 tables with foreign keys; credentials never logged (_redact); DATABASE_URL read at construction time; mock-based failure tests; live integration unverified (no test server available) |
| A4 | Done | scripts/import_json_to_postgres.py (new), tests/test_a4_import.py (new) | 383/383 full suite passes (23 new A4 tests); backup-first (timestamped copy before any DB work); v1/v2/v3 JSON transparent via JsonStorage; single-transaction import with ON CONFLICT DO NOTHING per entity type; skipped/inserted counts logged; rollback on any failure; failed backup aborts before DB; credentials never logged; live integration unverified (no test server available) |
| A5 | Done | app/config.py, run_web.py, app/services/student_manager.py, app/templates/index.html, app/static/js/app.js, app/static/css/style.css, tests/test_a5_pg_connect.py (new) | 396/396 full suite passes (13 new A5 tests); /api/pg/test and /api/pg/connect only registered when LOCAL_DEMO=1; loopback guard at route level; URL validated for postgresql:// scheme; credentials never returned/logged; failed connect keeps previous backend; psycopg2 ImportError path returns static 503 (no URL echo); masked input with eye toggle in UI; live integration unverified (no test server) |
| A6 | Done | app/storage/sqlite_storage.py, run_web.py, app/templates/index.html, app/static/js/app.js, app/static/css/style.css, tests/test_a6_classes_ui.py (new) | 414/414 full suite passes (18 new A6 tests); SqliteStorage v3 adds classes/enrollments tables with FK; save_dataset/load_dataset atomically persist all three collections; /api/classes CRUD + /api/enrollments + /api/classes/<id>/students routes; ClassManager loaded at startup from full dataset; _save_dataset() delegates to manager._storage so injected test backends work; Classes tab with selector bar, table, create/edit modal, enrollment panel with enroll/remove toggles; all-students view; stale-response guard: roster only returns students enrolled in the selected class |
