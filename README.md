# 📚 Student Grade Management System

A **modular, scalable, and clean** console-based application for managing student grades built in Python.

---

## 📂 Project Structure

```
student-grade-system/
│
├── main.py                          # Entry point — wires all layers
│
├── app/                             # Application package
│   ├── __init__.py
│   ├── config.py                    # Central configuration constants
│   │
│   ├── models/                      # Data layer
│   │   ├── __init__.py
│   │   └── student.py               # Student entity class
│   │
│   ├── validators/                  # Validation layer
│   │   ├── __init__.py
│   │   └── input_validator.py       # Reusable validation rules
│   │
│   ├── storage/                     # Persistence layer (pluggable)
│   │   ├── __init__.py
│   │   ├── base_storage.py          # Abstract interface
│   │   └── json_storage.py          # JSON file implementation
│   │
│   ├── services/                    # Business logic layer
│   │   ├── __init__.py
│   │   ├── student_manager.py       # CRUD + search + sort
│   │   └── statistics_service.py    # Grade statistics computation
│   │
│   └── ui/                          # Presentation layer
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
│   ├── test_validators.py
│   └── test_storage.py
│
├── data/                            # Persistent storage (auto-created)
│   └── students.json
│
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

```bash
# Run the application
python main.py

# Run all tests
python -m pytest tests/ -v

# Or with unittest
python -m unittest discover -s tests -v
```

---

## 📋 Features

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
- **test_validators.py** — Name, grade, index validation + boundary cases
- **test_storage.py** — JSON roundtrip, missing file, corrupted file handling
