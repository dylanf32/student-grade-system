# 📚 Student Grade Management System

A **modular, scalable, and clean** Python application for managing student grades — available as both a **web dashboard** (Flask) and a **console interface**.

---
<p align="center">
  <img src="https://img.shields.io/badge/version-2.0.0-blue.svg" alt="Version">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/status-active-brightgreen.svg" alt="Status">
  <img src="https://img.shields.io/badge/platform-Web%20%7C%20Console-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/built%20with-Python-3776AB?logo=python&logoColor=white" alt="Built With Python">
  <img src="https://img.shields.io/badge/framework-Flask-000000?logo=flask&logoColor=white" alt="Framework Flask">
  <img src="https://img.shields.io/badge/storage-SQLite%20%7C%20PostgreSQL-003B57?logo=sqlite&logoColor=white" alt="Storage">
</p>


## 📂 Project Structure

```
student-grade-system/
│
├── main.py                          # Console entry point — wires all layers
├── run_web.py                       # Web dashboard entry point (Flask + all REST routes)
├── migrate_to_sqlite.py             # One-off migration: JSON → SQLite
│
├── app/                             # Application package
│   ├── __init__.py
│   ├── config.py                    # Central configuration constants
│   │
│   ├── models/                      # Data layer
│   │   ├── __init__.py
│   │   ├── student.py               # Student + CourseGrade entity classes
│   │   ├── class_record.py          # ClassRecord entity class
│   │   ├── gradebook.py             # Gradebook / weighted-grade models
│   │   └── deadline.py              # Deadline entity class
│   │
│   ├── validators/                  # Validation layer
│   │   ├── __init__.py
│   │   └── input_validator.py       # Reusable validation rules
│   │
│   ├── storage/                     # Persistence layer (pluggable)
│   │   ├── __init__.py
│   │   ├── base_storage.py          # Abstract interface
│   │   ├── json_storage.py          # JSON file implementation (v1/v2/v3)
│   │   ├── sqlite_storage.py        # SQLite implementation (default)
│   │   ├── postgres_storage.py      # PostgreSQL implementation (optional)
│   │   └── deadline_storage.py      # JSON file implementation (deadlines)
│   │
│   ├── services/                    # Business logic layer
│   │   ├── __init__.py
│   │   ├── student_manager.py       # CRUD + search + sort + groups
│   │   ├── class_manager.py         # Class CRUD + enrollment management
│   │   ├── gradebook_service.py     # Weighted grade calculation
│   │   ├── statistics_service.py    # Grade statistics computation
│   │   └── insights_service.py      # At-risk student flagging
│   │
│   ├── templates/
│   │   └── index.html               # Single-page web dashboard
│   │
│   ├── static/
│   │   ├── css/style.css            # Dashboard styles
│   │   └── js/app.js                # Dashboard frontend controller
│   │
│   └── ui/                          # Console presentation layer
│       ├── __init__.py
│       ├── colors.py                # ANSI color utilities
│       ├── display.py               # Console rendering helpers
│       ├── input_helpers.py         # Safe input with validation
│       └── handlers.py              # Menu option handlers
│
├── tests/                           # Unit & integration tests
│   ├── __init__.py
│   ├── test_student.py              # Core model tests
│   ├── test_student_manager.py      # CRUD, search, sort
│   ├── test_statistics.py           # Statistics computation
│   ├── test_insights.py             # At-risk flagging
│   ├── test_validators.py           # Input validation rules
│   ├── test_storage.py              # JSON storage round-trips
│   ├── test_sqlite_storage.py       # SQLite storage round-trips
│   ├── test_regression.py           # Boundary and legacy-data regression
│   ├── test_stage2_fields.py        # linkedin_url, department, groups fields
│   ├── test_a1_classes.py           # ClassRecord + ClassManager + enrollments
│   ├── test_a2_gradebook.py         # Gradebook, weighted grades, term GPA
│   ├── test_a3_postgres.py          # PostgreSQL storage (requires psycopg2)
│   ├── test_a4_import.py            # JSON→SQLite import script
│   ├── test_a5_pg_connect.py        # /api/pg/connect + /api/pg/test endpoints
│   ├── test_a6_classes_ui.py        # Classes tab REST endpoints
│   ├── test_f1_save_failures.py     # HTTP 503 rollback on save failures
│   └── test_f2_validation.py        # Boolean grade/GPA + field validation
│
├── scripts/
│   └── import_json_to_postgres.py   # Bulk import from JSON → PostgreSQL
│
├── data/                            # Persistent storage (auto-created)
│   ├── students.db                  # SQLite database (default)
│   └── deadlines.json               # Deadline data (JSON)
│
├── requirements.txt
└── README.md
```

---

## 🏗️ Architecture Principles

| Principle | How It's Applied |
|---|---|
| **Separation of Concerns** | Models, Services, Storage, UI, and Validators are in separate packages |
| **Dependency Injection** | `StudentManager` receives a `BaseStorage` — swap SQLite for PostgreSQL without touching business logic |
| **Single Responsibility** | Each class/module does exactly one thing |
| **Open/Closed** | Add new storage backends by subclassing `BaseStorage`; add features by adding a handler |
| **No Side Effects in Services** | Service layer raises exceptions, never prints — UI handles all output |
| **Centralized Config** | All constants live in `config.py` |
| **Testability** | Services are tested with `FakeStorage` or in-memory SQLite — zero disk I/O in unit tests |

---

## 🚀 How to Run

### Web Dashboard (recommended)

```bash
# Install dependencies
pip install -r requirements.txt

# Start the Flask server
python run_web.py
```

Then open **http://localhost:5000** in your browser.

### Enable PostgreSQL UI (optional, local dev only)

```bash
LOCAL_DEMO=1 python run_web.py
```

### Console Interface

```bash
python main.py
```

### Tests

```bash
python -m pytest tests/ -v
```

---

## 📋 Features

### 🌐 Web Dashboard

| Feature | Description |
|---|---|
| **Student Directory** | Add, edit, delete, search, filter, and sort students in a live table |
| **Generate Students** | One-click generation of up to 100 realistic random students with randomized names, majors, grades, and courses |
| **Grade Statistics** | Class average, highest grade, passing rate, and avg GPA — animated stat cards |
| **Analytics Charts** | Grade distribution, academic standing donut, pass/fail ratio, students by major |
| **At-Risk Panel** | Automatically flags students below the passing threshold |
| **Deadline Reminders** | Track assignment, exam, and project due dates with 7 / 3 / 1-day toast notifications |
| **Deadlines Tab** | Full CRUD table for all deadlines — add, edit, delete, with urgency colour-coding |
| **Classes Tab** | Create and manage shared classes; enroll/unenroll students per class |
| **Student Profiles** | Per-student detail view with GPA, academic standing, courses, LinkedIn, department, and groups |
| **Groups & Departments** | Assign students to named groups and departments; filter by either |
| **Persistent Storage** | All data saved to SQLite (default) or PostgreSQL with atomic rollback on save failure |
| **PostgreSQL Mode** | Live-switch to a PostgreSQL backend from the UI (requires `LOCAL_DEMO=1`) |

### 🖥️ Console Interface

| # | Feature | Menu Option |
|---|---|---|
| 1 | ➕ Add Student (with name + grade validation) | 1 |
| 2 | ➖ Remove Student by index | 2 |
| 3 | ✏️ Update Grade | 3 |
| 4 | 📄 View All Students (color-coded table) | 4 |
| 5 | 🔍 Search by Name (case-insensitive) | 5 |
| 6 | 📊 Statistics (avg, max, min, pass/fail) | 6 |
| 7 | 🔃 Sort by Grade (asc/desc) | 7 |
| 8 | 💾 Save to JSON | 8 |
| 9 | 🚪 Exit (auto-saves) | 9 |

---

## 🗄️ Storage Backends

| Backend | File | Notes |
|---|---|---|
| **SQLite** (default) | `data/students.db` | Zero-dependency, ships with Python; used by the web dashboard |
| **JSON** | `data/students.json` | Legacy flat-file format; still supported for imports and the console |
| **PostgreSQL** | env `DATABASE_URL` | Production-grade; enable via `LOCAL_DEMO=1` or set `DATABASE_URL` |

Migrate existing JSON data to SQLite:

```bash
python migrate_to_sqlite.py
```

---

## 🌐 REST API Reference

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/students` | List all students |
| POST | `/api/students` | Add a student |
| PUT | `/api/students/<id>` | Update a student (partial) |
| DELETE | `/api/students/<id>` | Delete a student |
| POST | `/api/seed` | Generate `n` random students (1–100) |
| POST | `/api/seed/classes` | Generate `n` random classes (1–50) |
| POST | `/api/seed/deadlines` | Generate `n` random deadlines (1–100) |
| GET | `/api/stats` | Grade statistics + distributions |
| GET | `/api/insights` | At-risk student flags |
| GET | `/api/search?name=…` | Search students by name |
| GET | `/api/filter` | Filter by name/major/year/standing/grade |
| GET | `/api/sort?ascending=…` | Sort students by grade |
| POST | `/api/save` | Persist current state |
| GET | `/api/classes` | List all classes |
| POST | `/api/classes` | Create a class |
| PUT | `/api/classes/<id>` | Update a class |
| DELETE | `/api/classes/<id>` | Delete a class |
| GET | `/api/classes/<id>/students` | Students enrolled in a class |
| POST | `/api/enrollments` | Enroll a student in a class |
| DELETE | `/api/enrollments` | Unenroll a student |
| GET/POST/PUT/DELETE | `/api/deadlines` | Deadline CRUD |
| GET | `/api/deadlines/upcoming` | Deadlines due within 7 days |
| GET | `/api/config` | Grade boundary constants |

---

## 🧪 Test Coverage

- **test_student.py** — Model creation, validation, serialization, equality
- **test_student_manager.py** — CRUD, search, sort, persistence (with FakeStorage)
- **test_statistics.py** — Compute, accessors, empty-list edge cases
- **test_insights.py** — At-risk flagging, threshold boundaries, InsightsService
- **test_validators.py** — Name, grade, index validation + boundary cases
- **test_storage.py** — JSON round-trip, missing file, corrupted file handling
- **test_sqlite_storage.py** — SQLite round-trips, in-memory backend
- **test_regression.py** — Decimal grades, threshold boundaries, bare-filename storage, duplicate name search
- **test_stage2_fields.py** — `linkedin_url`, `department`, `groups` fields and group management
- **test_a1_classes.py** — `ClassRecord` + `ClassManager` + enrollment CRUD
- **test_a2_gradebook.py** — Gradebook, weighted grades, term GPA calculation
- **test_a3_postgres.py** — PostgreSQL storage backend
- **test_a4_import.py** — JSON→SQLite import script validation
- **test_a5_pg_connect.py** — `/api/pg/connect` and `/api/pg/test` endpoints
- **test_a6_classes_ui.py** — Classes tab REST endpoints (full integration)
- **test_f1_save_failures.py** — HTTP 503 + rollback when save fails
- **test_f2_validation.py** — Boolean grade/GPA rejection, non-string field validation


## License

Distributed under the MIT License. See the [LICENSE](LICENSE) file for details.
