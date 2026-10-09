# 📚 Student Grade Management System

A **modular, scalable, and clean** Python application for managing student grades — available as both a **web dashboard** (Flask) and a **console interface**.

---
<p align="center">
  <img src="https://img.shields.io/badge/version-1.0.0-blue.svg" alt="Version">
  <a href="https://opensource.org/licenses/MIT"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/status-active-brightgreen.svg" alt="Status">
  <img src="https://img.shields.io/badge/platform-Web%20%7C%20Console-lightgrey.svg" alt="Platform">
  <img src="https://img.shields.io/badge/built%20with-Python-3776AB?logo=python&logoColor=white" alt="Built With Python">
  <img src="https://img.shields.io/badge/framework-Flask-000000?logo=flask&logoColor=white" alt="Framework Flask">
</p>


## 📂 Project Structure

```
student-grade-system/
│
├── main.py                          # Console entry point — wires all layers
├── run_web.py                       # Web dashboard entry point (Flask)
│
├── app/                             # Application package
│   ├── __init__.py
│   ├── config.py                    # Central configuration constants
│   │
│   ├── models/                      # Data layer
│   │   ├── __init__.py
│   │   ├── student.py               # Student entity class
│   │   └── deadline.py              # Deadline entity class
│   │
│   ├── validators/                  # Validation layer
│   │   ├── __init__.py
│   │   └── input_validator.py       # Reusable validation rules
│   │
│   ├── storage/                     # Persistence layer (pluggable)
│   │   ├── __init__.py
│   │   ├── base_storage.py          # Abstract interface
│   │   ├── json_storage.py          # JSON file implementation (students)
│   │   └── deadline_storage.py      # JSON file implementation (deadlines)
│   │
│   ├── services/                    # Business logic layer
│   │   ├── __init__.py
│   │   ├── student_manager.py       # CRUD + search + sort
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
├── tests/                           # Unit tests
│   ├── __init__.py
│   ├── test_student.py
│   ├── test_student_manager.py
│   ├── test_statistics.py
│   ├── test_insights.py
│   ├── test_validators.py
│   ├── test_storage.py
│   └── test_regression.py
│
├── data/                            # Persistent storage (auto-created)
│   ├── students.json
│   └── deadlines.json
│
├── requirements.txt
└── README.md
```

---

## 🏗️ Architecture Principles

| Principle | How It's Applied |
|---|---|
| **Separation of Concerns** | Models, Services, Storage, UI, and Validators are in separate packages |
| **Dependency Injection** | `StudentManager` receives a `BaseStorage` — swap JSON for SQLite without touching business logic |
| **Single Responsibility** | Each class/module does exactly one thing |
| **Open/Closed** | Add new storage backends by subclassing `BaseStorage`; add features by adding a handler |
| **No Side Effects in Services** | Service layer raises exceptions, never prints — UI handles all output |
| **Centralized Config** | All constants live in `config.py` |
| **Testability** | Services are tested with `FakeStorage` — zero disk I/O in unit tests |

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
| **Grade Statistics** | Class average, highest grade, passing rate, and avg GPA — animated stat cards |
| **Analytics Charts** | Grade distribution, academic standing donut, pass/fail ratio, students by major |
| **At-Risk Panel** | Automatically flags students below the passing threshold |
| **Deadline Reminders** | Track assignment, exam, and project due dates with 7 / 3 / 1-day toast notifications |
| **Deadlines Tab** | Full CRUD table for all deadlines — add, edit, delete, with urgency colour-coding |
| **Persistent Storage** | All data saved to JSON files; atomic writes prevent data loss |

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

## 🧪 Test Coverage

- **test_student.py** — Model creation, validation, serialization, equality
- **test_student_manager.py** — CRUD, search, sort, persistence (with FakeStorage)
- **test_statistics.py** — Compute, accessors, empty-list edge cases
- **test_insights.py** — At-risk flagging, threshold boundaries, InsightsService
- **test_validators.py** — Name, grade, index validation + boundary cases
- **test_storage.py** — JSON roundtrip, missing file, corrupted file handling
- **test_regression.py** — Decimal grades, threshold boundaries, bare-filename storage, duplicate name search


## License

Distributed under the MIT License. See the [LICENSE](LICENSE) file for details.
