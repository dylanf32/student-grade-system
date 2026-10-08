# Student Grade Management System

A Python application with a Flask web dashboard and a console interface for managing student grades and academic profiles.

This repository is Dylan Ferrer's extension of [samin-developer/student-grade-system](https://github.com/samin-developer/student-grade-system), developed for the IBM Bob hackathon. The original project and MIT attribution are preserved.

**Stack:** Python · Flask · HTML/CSS/JavaScript · JSON persistence

## Features

- Add, update, remove, search, filter, and sort students.
- Store email, major, academic year, GPA, courses, and academic notes.
- View grade summaries, passing rates, and GPA, standing, and major distributions.
- Use stable UUIDs for web update/delete requests.
- Save JSON through a temporary file and atomic replacement.
- Use either the web dashboard or console menus.

Academic standing and GPA calculations are application-defined examples; they do not represent a university's official grading policy.

## Setup

```powershell
git clone https://github.com/dylanf32/student-grade-system.git
cd student-grade-system
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

On macOS/Linux, activate with `source .venv/bin/activate`. The source uses Python 3.10+ type syntax.

## Run

### Web dashboard

```bash
python run_web.py
```

Open [http://localhost:5000](http://localhost:5000). The `PORT` environment variable can change the port. The script binds to `0.0.0.0` and does not implement authentication; use it as a local demonstration with sample data.

### Console

```bash
python main.py
```

Follow the menu to manage students, inspect statistics, and save data.

## Storage

Records are stored in `data/students.json`. The repository includes starter records. Back up that file before experimenting if you want to keep its current contents. JSON persistence is designed for this demonstration; atomic writes alone do not provide concurrent multi-worker database semantics.

## Architecture

| Path | Responsibility |
| --- | --- |
| [run_web.py](run_web.py) | Flask routes and web API |
| [main.py](main.py) | Console entry point |
| `app/models/` | Student and course records |
| `app/services/` | Student operations and summary statistics |
| `app/storage/` | Storage interface and JSON implementation |
| `app/validators/` | Input validation |
| `app/ui/` | Console display and input |
| `app/templates/`, `app/static/` | Web dashboard |
| `tests/` | Model, service, storage, validation, and regression tests |

## Tests

The included unittest suite can run without installing pytest:

```bash
python -m unittest discover -s tests -v
```

Alternatively, install pytest separately and run `python -m pytest tests/ -v`.

## Hackathon development

- [Hackathon plan](HACKATHON_PLAN.md): intended scope and project planning.
- [AI prompt log](ai-prompts/README.md): IBM Bob prompts and development sessions.
- [Code audit plan](code-audit-fixes-plan.md): recorded audit findings and fixes.

Plans describe proposed work; the implemented behavior is defined by the source. AI assistance is documented in the prompt log.

## License and attribution

Distributed under the [MIT License](LICENSE). Original project: [samin-developer/student-grade-system](https://github.com/samin-developer/student-grade-system). Extensions in this fork are maintained by [Dylan Ferrer](https://github.com/dylanf32).
