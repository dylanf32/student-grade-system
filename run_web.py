import os
import random
from datetime import date, datetime
from flask import Flask, jsonify, request, render_template
from app.validators.input_validator import InputValidator as _IV

from app.storage.sqlite_storage import SqliteStorage
from app.storage.deadline_storage import DeadlineStorage
from app.services.student_manager import StudentManager
from app.services.class_manager import ClassManager
from app.services.statistics_service import StatisticsService
from app.services.insights_service import InsightsService
from app.models.student import Student, CourseGrade
from app.models.class_record import ClassRecord
from app.models.deadline import Deadline
from app.config import MIN_GRADE, MAX_GRADE, PASSING_THRESHOLD, DEFAULT_DB_FILE, LOCAL_DEMO_MODE

# Set directories relative to this file
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Initialize Storage & StudentManager
storage = SqliteStorage(DEFAULT_DB_FILE)
manager = StudentManager(storage)

# Initialize ClassManager and load full dataset
class_manager = ClassManager()
_dataset = storage.load_dataset()
with manager._lock:
    manager._students = _dataset.students
class_manager.load_from_data(_dataset.classes, _dataset.enrollments)


def _save_dataset() -> bool:
    """Persist students + classes + enrollments atomically.

    Delegates to manager._storage so that test-injected backends are respected.
    """
    with manager._lock:
        snapshot = list(manager._students)
    return manager._storage.save_dataset(
        students=snapshot,
        classes=class_manager.classes_to_list(),
        enrollments=class_manager.enrollments_to_list(),
    )


# Initialize Deadline Storage
deadline_storage = DeadlineStorage()
_deadlines: list[Deadline] = deadline_storage.load()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def student_to_payload(s: Student, index: int) -> dict:
    """Serialise a Student to the JSON shape sent to the frontend."""
    computed_gpa = s.gpa
    if computed_gpa is None:
        computed_gpa = s.compute_gpa_from_courses()
    if computed_gpa is None and s.grade is not None:
        computed_gpa = round(s.grade / 25.0, 2)

    return {
        "index": index,
        "student_id": s.id,
        "id": f"STU-{index + 1:03d}",
        "name": s.name,
        "grade": s.grade,
        "email": s.email,
        "major": s.major,
        "academic_year": s.academic_year,
        "gpa": computed_gpa,
        "courses": [c.to_dict() for c in s.courses],
        "notes": s.notes,
        "standing": s.academic_standing(),
        "linkedin_url": s.linkedin_url,
        "department": s.department,
        "groups": s.groups,
    }


# ---------------------------------------------------------------------------
# Config & root
# ---------------------------------------------------------------------------

@app.route('/api/config', methods=['GET'])
def get_config():
    """Expose grade boundary constants so the frontend stays in sync with config.py."""
    return jsonify({
        "min_grade": MIN_GRADE,
        "max_grade": MAX_GRADE,
        "passing_threshold": PASSING_THRESHOLD,
        "local_demo": LOCAL_DEMO_MODE,
    })


@app.route('/')
def index():
    """Serve the web application dashboard."""
    return render_template('index.html')


# ---------------------------------------------------------------------------
# Students — CRUD
# ---------------------------------------------------------------------------

@app.route('/api/students', methods=['GET'])
def get_students():
    """Retrieve all students."""
    students = manager.get_all_students()
    return jsonify([student_to_payload(s, i) for i, s in enumerate(students)])


def _parse_courses(raw_courses) -> tuple:
    """Validate and parse a list of course dicts.

    Returns (courses_list, error_string_or_None).
    """
    if not isinstance(raw_courses, list):
        return None, "courses must be a list."
    courses = []
    for i, c in enumerate(raw_courses):
        if not isinstance(c, dict):
            return None, f"Course entry {i} must be an object."
        name_val = c.get("course")
        if not isinstance(name_val, str) or not name_val.strip():
            return None, f"Course entry {i}: 'course' must be a nonempty string."
        grade_val = c.get("grade")
        valid, msg = _IV.validate_course_grade(grade_val)
        if not valid:
            return None, f"Course entry {i} ({name_val!r}): {msg}"
        # Convert numeric string grade to float before constructing
        if isinstance(grade_val, str):
            grade_val = float(grade_val)
        courses.append(CourseGrade(course=name_val.strip(), grade=grade_val))
    return courses, None


@app.route('/api/students', methods=['POST'])
def add_student():
    """Add a new student with validation."""
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400

    # --- name ---
    name_raw = data.get("name")
    if not isinstance(name_raw, str):
        return jsonify({"success": False, "error": "name must be a string."}), 400
    name = name_raw.strip()

    # --- grade (required, no null, no boolean) ---
    grade_raw = data.get("grade")
    if grade_raw is None:
        return jsonify({"success": False, "error": "Grade is required."}), 400
    if isinstance(grade_raw, bool):
        return jsonify({"success": False, "error": "Grade must be a number."}), 400
    try:
        grade_val = float(grade_raw)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Grade must be a number."}), 400

    # --- courses ---
    raw_courses = data.get("courses") or []
    courses, err = _parse_courses(raw_courses)
    if err:
        return jsonify({"success": False, "error": err}), 400

    # --- GPA (optional) ---
    gpa_raw = data.get("gpa")
    if gpa_raw in (None, ""):
        gpa = None
    else:
        valid, msg = _IV.validate_gpa(gpa_raw)
        if not valid:
            return jsonify({"success": False, "error": msg}), 400
        gpa = float(gpa_raw) if isinstance(gpa_raw, str) else gpa_raw

    # --- text fields: reject non-strings ---
    for field in ("email", "major", "academic_year", "notes", "linkedin_url", "department"):
        val = data.get(field)
        if val is not None and not isinstance(val, str):
            return jsonify({"success": False, "error": f"{field} must be a string."}), 400

    # --- groups ---
    raw_groups = data.get("groups") or []
    if not isinstance(raw_groups, list):
        return jsonify({"success": False, "error": "groups must be a list."}), 400
    groups = [str(g).strip() for g in raw_groups if isinstance(g, str) and str(g).strip()]

    try:
        student = manager.add_student(
            name=name,
            grade=grade_val,
            email=data.get("email", ""),
            major=data.get("major", ""),
            academic_year=data.get("academic_year", ""),
            gpa=gpa,
            courses=courses,
            notes=data.get("notes", ""),
            linkedin_url=data.get("linkedin_url", ""),
            department=data.get("department", ""),
            groups=groups,
        )
        if not _save_dataset():
            # Roll back: remove the student that was just added in memory.
            all_students = manager.get_all_students()
            rollback_idx = next((i for i, s in enumerate(all_students) if s.id == student.id), None)
            if rollback_idx is not None:
                manager.remove_student(rollback_idx)
            return jsonify({"success": False, "error": "Student could not be saved. Please try again."}), 503
        students = manager.get_all_students()
        idx = next(i for i, s in enumerate(students) if s.id == student.id)
        return jsonify({"success": True, "student": student_to_payload(student, idx)})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/students/<student_id>', methods=['PUT'])
def update_student(student_id):
    """Update a student's fields identified by their stable UUID.

    Accepts a partial update — only fields present in the JSON body are changed.
    Validates ALL supplied fields before applying any.
    """
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400

    # Validate all supplied fields first; collect into `fields` only after all pass.
    fields = {}

    if "grade" in data:
        grade_raw = data["grade"]
        if isinstance(grade_raw, bool):
            return jsonify({"success": False, "error": "Grade must be a number."}), 400
        try:
            grade_parsed = float(grade_raw)
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Grade must be a number."}), 400
        valid, msg = _IV.validate_grade(grade_parsed)
        if not valid:
            return jsonify({"success": False, "error": msg}), 400
        fields["grade"] = grade_parsed

    for field in ("email", "major", "academic_year", "notes", "linkedin_url", "department"):
        if field in data:
            val = data[field]
            if not isinstance(val, str):
                return jsonify({"success": False, "error": f"{field} must be a string."}), 400
            fields[field] = val

    if "groups" in data:
        raw_groups = data["groups"]
        if raw_groups is None:
            raw_groups = []
        if not isinstance(raw_groups, list):
            return jsonify({"success": False, "error": "groups must be a list."}), 400
        fields["groups"] = [str(g).strip() for g in raw_groups if isinstance(g, str) and str(g).strip()]

    if "gpa" in data:
        gpa_raw = data["gpa"]
        if gpa_raw in (None, ""):
            fields["gpa"] = None
        else:
            valid, msg = _IV.validate_gpa(gpa_raw)
            if not valid:
                return jsonify({"success": False, "error": msg}), 400
            fields["gpa"] = float(gpa_raw) if isinstance(gpa_raw, str) else gpa_raw

    if "courses" in data:
        raw_courses = data["courses"] or []
        courses, err = _parse_courses(raw_courses)
        if err:
            return jsonify({"success": False, "error": err}), 400
        fields["courses"] = courses

    if not fields:
        return jsonify({"success": False, "error": "No fields to update."}), 400

    # Snapshot the current state before mutating so we can roll back.
    existing = manager.get_by_id(student_id)
    if existing is None:
        return jsonify({"success": False, "error": "Student not found."}), 404
    old_fields = {
        "grade": existing.grade,
        "email": existing.email,
        "major": existing.major,
        "academic_year": existing.academic_year,
        "gpa": existing.gpa,
        "courses": existing.courses,
        "notes": existing.notes,
        "linkedin_url": existing.linkedin_url,
        "department": existing.department,
        "groups": existing.groups,
    }

    try:
        student = manager.update_student(student_id, **fields)
        if not _save_dataset():
            # Roll back: restore the previous field values.
            manager.update_student(student_id, **old_fields)
            return jsonify({"success": False, "error": "Update could not be saved. Please try again."}), 503
        students = manager.get_all_students()
        idx = next((i for i, s in enumerate(students) if s.id == student.id), 0)
        return jsonify({"success": True, "student": student_to_payload(student, idx)})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student identified by their stable UUID."""
    students = manager.get_all_students()
    index = next((i for i, s in enumerate(students) if s.id == student_id), None)
    if index is None:
        return jsonify({"success": False, "error": "Student not found."}), 404

    try:
        student = manager.remove_student(index)
        if not _save_dataset():
            # Roll back: re-insert the student at the original index.
            manager.insert_student_at(index, student)
            return jsonify({"success": False, "error": "Deletion could not be saved. Please try again."}), 503
        return jsonify({
            "success": True,
            "student": {"name": student.name, "grade": student.grade}
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------------------------------------------------------------------------
# Groups & Departments
# ---------------------------------------------------------------------------

@app.route('/api/groups', methods=['GET'])
def get_groups():
    """Return all distinct group names across the roster."""
    return jsonify(manager.list_groups())


@app.route('/api/departments', methods=['GET'])
def get_departments():
    """Return all distinct non-empty department names across the roster."""
    return jsonify(manager.list_departments())


@app.route('/api/students/<student_id>/groups', methods=['POST'])
def add_student_to_group(student_id):
    """Add a student to a group.  Body: {"group": "Group Name"}"""
    data = request.json or {}
    group = (data.get("group") or "").strip()
    if not group:
        return jsonify({"success": False, "error": "group is required."}), 400
    try:
        student = manager.assign_group(student_id, group)
        if not _save_dataset():
            manager.remove_from_group(student_id, group)
            return jsonify({"success": False, "error": "Could not save group assignment."}), 503
        students = manager.get_all_students()
        idx = next((i for i, s in enumerate(students) if s.id == student.id), 0)
        return jsonify({"success": True, "student": student_to_payload(student, idx)})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/students/<student_id>/groups/<group_name>', methods=['DELETE'])
def remove_student_from_group(student_id, group_name):
    """Remove a student from a group."""
    try:
        student = manager.remove_from_group(student_id, group_name)
        if not _save_dataset():
            manager.assign_group(student_id, group_name)
            return jsonify({"success": False, "error": "Could not save group removal."}), 503
        students = manager.get_all_students()
        idx = next((i for i, s in enumerate(students) if s.id == student.id), 0)
        return jsonify({"success": True, "student": student_to_payload(student, idx)})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


# ---------------------------------------------------------------------------
# Statistics
# ---------------------------------------------------------------------------

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retrieve current grade statistics plus academic standing distribution."""
    students = manager.get_all_students()
    stats = StatisticsService.compute(students)
    analytics = StatisticsService.compute_analytics(students)

    passing_rate = round(
        (stats.passing_count / stats.total_students * 100), 1
    ) if stats.total_students > 0 else 0.0

    # GPA distribution
    gpas = []
    for s in students:
        gpa = s.gpa
        if gpa is None:
            gpa = s.compute_gpa_from_courses()
        if gpa is None and s.grade is not None:
            gpa = round(s.grade / 25.0, 2)
        if gpa is not None:
            gpas.append(gpa)
    avg_gpa = round(sum(gpas) / len(gpas), 2) if gpas else None

    # Standing distribution
    standing_dist: dict = {}
    for s in students:
        st = s.academic_standing()
        standing_dist[st] = standing_dist.get(st, 0) + 1

    # Major distribution
    major_dist: dict = {}
    for s in students:
        m = s.major or "Undeclared"
        major_dist[m] = major_dist.get(m, 0) + 1

    return jsonify({
        "total_students": stats.total_students,
        "average": stats.average,
        "highest": stats.highest,
        "lowest": stats.lowest,
        "passing_count": stats.passing_count,
        "failing_count": stats.failing_count,
        "passing_rate": passing_rate,
        "avg_gpa": avg_gpa,
        "standing_distribution": standing_dist,
        "major_distribution": major_dist,
        "grade_distribution": analytics.distribution,
    })


# ---------------------------------------------------------------------------
# Insights
# ---------------------------------------------------------------------------

@app.route('/api/insights', methods=['GET'])
def get_insights():
    """Return per-student support flags derived from the shared passing threshold."""
    students = manager.get_all_students()
    insights = InsightsService.get_insights(students)
    return jsonify([
        {
            "student_id": i.student_id,
            "name": i.name,
            "grade": i.grade,
            "threshold": i.threshold,
            "status": i.status,
            "reason": i.reason,
        }
        for i in insights
    ])


# ---------------------------------------------------------------------------
# Search & Filter
# ---------------------------------------------------------------------------

@app.route('/api/search', methods=['GET'])
def search_student():
    """Search for students by name (case-insensitive, returns all matches)."""
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name query parameter is required."}), 400

    matches = manager.search_all_by_name(name)
    if not matches:
        return jsonify({"found": False, "students": []})

    students_payload = [student_to_payload(s, i) for i, s in matches]
    return jsonify({
        "found": True,
        "students": students_payload,
        # Backward-compatible single-match fields (first result)
        "index": students_payload[0]["index"],
        "student": students_payload[0],
    })


@app.route('/api/filter', methods=['GET'])
def filter_students():
    """Filter students by multiple criteria.

    Query parameters (all optional, all substring matches):
      name, major, academic_year, standing, min_grade, max_grade
    """
    name = request.args.get("name", "").strip()
    major = request.args.get("major", "").strip()
    academic_year = request.args.get("academic_year", "").strip()
    standing = request.args.get("standing", "").strip()

    min_grade = None
    max_grade = None
    try:
        if request.args.get("min_grade", "") != "":
            min_grade = float(request.args["min_grade"])
        if request.args.get("max_grade", "") != "":
            max_grade = float(request.args["max_grade"])
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "min_grade / max_grade must be numbers."}), 400

    matches = manager.filter_students(
        name=name,
        major=major,
        academic_year=academic_year,
        standing=standing,
        min_grade=min_grade,
        max_grade=max_grade,
    )
    return jsonify([student_to_payload(s, i) for i, s in matches])


# ---------------------------------------------------------------------------
# Sort & Save
# ---------------------------------------------------------------------------

@app.route('/api/sort', methods=['GET'])
def sort_students():
    """Sort students by grade in-place and return the sorted list."""
    ascending = request.args.get("ascending", "true").lower() == "true"
    manager.sort_by_grade(ascending)
    saved = _save_dataset()
    students = manager.get_all_students()
    payload = [student_to_payload(s, i) for i, s in enumerate(students)]
    if not saved:
        # Sort succeeded in memory; warn the client that the order was not persisted.
        return jsonify({"success": False, "error": "Sort order could not be saved.", "students": payload}), 503
    return jsonify(payload)


@app.route('/api/save', methods=['POST'])
def save_data():
    """Save data to the persistence layer."""
    success = _save_dataset()
    if not success:
        return jsonify({"success": False, "error": "Could not save data. Please try again."}), 503
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Classes — CRUD
# ---------------------------------------------------------------------------

def _class_payload(c: ClassRecord) -> dict:
    """Serialise a ClassRecord to the JSON shape sent to the frontend."""
    return {
        "id":         c.id,
        "code":       c.code,
        "title":      c.title,
        "credits":    c.credits,
        "term_start": c.term_start.isoformat() if c.term_start else None,
        "term_end":   c.term_end.isoformat() if c.term_end else None,
        "student_count": len(class_manager.get_students_in_class(c.id)),
    }


@app.route('/api/classes', methods=['GET'])
def get_classes():
    """Return all classes."""
    return jsonify([_class_payload(c) for c in class_manager.get_all_classes()])


@app.route('/api/classes', methods=['POST'])
def add_class():
    """Create a new class."""
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400
    code_raw  = data.get("code")
    title_raw = data.get("title")
    if not isinstance(code_raw, str) or not code_raw.strip():
        return jsonify({"success": False, "error": "code must be a nonempty string."}), 400
    if not isinstance(title_raw, str) or not title_raw.strip():
        return jsonify({"success": False, "error": "title must be a nonempty string."}), 400

    credits_raw = data.get("credits", 3.0)
    if isinstance(credits_raw, bool):
        return jsonify({"success": False, "error": "credits must be a number."}), 400
    try:
        credits_val = float(credits_raw)
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "credits must be a number."}), 400

    # Optional dates
    from datetime import date as _date
    def _parse_date(raw):
        if not raw:
            return None
        try:
            return _date.fromisoformat(raw)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid date: {raw!r}")

    try:
        term_start = _parse_date(data.get("term_start"))
        term_end   = _parse_date(data.get("term_end"))
        record = class_manager.add_class(
            code=code_raw.strip(),
            title=title_raw.strip(),
            credits=credits_val,
            term_start=term_start,
            term_end=term_end,
        )
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    if not _save_dataset():
        class_manager.delete_class(record.id)
        return jsonify({"success": False, "error": "Class could not be saved. Please try again."}), 503

    return jsonify({"success": True, "class": _class_payload(record)})


@app.route('/api/classes/<class_id>', methods=['PUT'])
def update_class(class_id):
    """Update an existing class."""
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400

    record = class_manager.get_class(class_id)
    if record is None:
        return jsonify({"success": False, "error": "Class not found."}), 404

    # Snapshot for rollback
    old = record.to_dict()

    fields = {}
    for field in ("code", "title"):
        if field in data:
            val = data[field]
            if not isinstance(val, str) or not val.strip():
                return jsonify({"success": False, "error": f"{field} must be a nonempty string."}), 400
            fields[field] = val.strip()

    if "credits" in data:
        cv = data["credits"]
        if isinstance(cv, bool):
            return jsonify({"success": False, "error": "credits must be a number."}), 400
        try:
            fields["credits"] = float(cv)
        except (TypeError, ValueError):
            return jsonify({"success": False, "error": "credits must be a number."}), 400

    from datetime import date as _date
    for f in ("term_start", "term_end"):
        if f in data:
            raw = data[f]
            if raw:
                try:
                    fields[f] = _date.fromisoformat(raw)
                except (ValueError, TypeError):
                    return jsonify({"success": False, "error": f"Invalid date for {f}."}), 400
            else:
                fields[f] = None

    if not fields:
        return jsonify({"success": False, "error": "No fields to update."}), 400

    try:
        updated = class_manager.update_class(class_id, **fields)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    if not _save_dataset():
        # Rollback
        try:
            from datetime import date as _date2
            rb = {}
            rb["code"] = old["code"]
            rb["title"] = old["title"]
            rb["credits"] = old["credits"]
            rb["term_start"] = _date2.fromisoformat(old["term_start"]) if old.get("term_start") else None
            rb["term_end"] = _date2.fromisoformat(old["term_end"]) if old.get("term_end") else None
            class_manager.update_class(class_id, **rb)
        except Exception:
            pass
        return jsonify({"success": False, "error": "Update could not be saved. Please try again."}), 503

    return jsonify({"success": True, "class": _class_payload(updated)})


@app.route('/api/classes/<class_id>', methods=['DELETE'])
def delete_class(class_id):
    """Delete a class (must have no enrolled students)."""
    try:
        record = class_manager.delete_class(class_id)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

    if not _save_dataset():
        # Re-add the class on failure
        try:
            from app.models.class_record import ClassRecord as _CR
            cr = _CR.from_dict(record.to_dict())
            class_manager._classes[cr.id] = cr
        except Exception:
            pass
        return jsonify({"success": False, "error": "Deletion could not be saved. Please try again."}), 503

    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Enrollments
# ---------------------------------------------------------------------------

@app.route('/api/classes/<class_id>/students', methods=['GET'])
def get_class_students(class_id):
    """Return student UUIDs enrolled in a class."""
    if class_manager.get_class(class_id) is None:
        return jsonify({"success": False, "error": "Class not found."}), 404
    student_ids = class_manager.get_students_in_class(class_id)
    students = manager.get_all_students()
    enrolled = [student_to_payload(s, i) for i, s in enumerate(students) if s.id in student_ids]
    return jsonify(enrolled)


@app.route('/api/enrollments', methods=['POST'])
def enroll_student():
    """Enroll a student in a class. Body: {"student_id": …, "class_id": …}"""
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400
    student_id = (data.get("student_id") or "").strip()
    class_id   = (data.get("class_id")   or "").strip()
    if not student_id:
        return jsonify({"success": False, "error": "student_id is required."}), 400
    if not class_id:
        return jsonify({"success": False, "error": "class_id is required."}), 400
    if manager.get_by_id(student_id) is None:
        return jsonify({"success": False, "error": "Student not found."}), 404
    try:
        class_manager.enroll(student_id, class_id)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    if not _save_dataset():
        class_manager.unenroll(student_id, class_id)
        return jsonify({"success": False, "error": "Enrollment could not be saved. Please try again."}), 503
    return jsonify({"success": True, "enrolled": True})


@app.route('/api/enrollments', methods=['DELETE'])
def unenroll_student():
    """Unenroll a student from a class. Body: {"student_id": …, "class_id": …}"""
    data = request.json
    if not isinstance(data, dict):
        return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400
    student_id = (data.get("student_id") or "").strip()
    class_id   = (data.get("class_id")   or "").strip()
    if not student_id:
        return jsonify({"success": False, "error": "student_id is required."}), 400
    if not class_id:
        return jsonify({"success": False, "error": "class_id is required."}), 400
    try:
        class_manager.unenroll(student_id, class_id)
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400
    if not _save_dataset():
        try:
            class_manager.enroll(student_id, class_id)
        except Exception:
            pass
        return jsonify({"success": False, "error": "Unenrollment could not be saved. Please try again."}), 503
    return jsonify({"success": True, "enrolled": False})


@app.route('/api/students/<student_id>/classes', methods=['GET'])
def get_student_classes(student_id):
    """Return classes a student is enrolled in."""
    if manager.get_by_id(student_id) is None:
        return jsonify({"success": False, "error": "Student not found."}), 404
    classes = class_manager.get_classes_for_student(student_id)
    return jsonify([_class_payload(c) for c in classes])




# ---------------------------------------------------------------------------
# Deadlines — CRUD + upcoming
# ---------------------------------------------------------------------------

def _deadline_payload(d: Deadline, today: date) -> dict:
    """Serialize a Deadline to the JSON shape sent to the frontend."""
    try:
        due = datetime.strptime(d.due_date, "%Y-%m-%d").date()
        days_left = (due - today).days
    except ValueError:
        days_left = None

    urgency = "none"
    if days_left is not None:
        if days_left < 0:
            urgency = "overdue"
        elif days_left <= 1:
            urgency = "critical"
        elif days_left <= 3:
            urgency = "high"
        elif days_left <= 7:
            urgency = "medium"

    return {
        "id": d.id,
        "title": d.title,
        "type": d.type,
        "due_date": d.due_date,
        "course": d.course,
        "description": d.description,
        "student_id": d.student_id,
        "days_left": days_left,
        "urgency": urgency,
    }


@app.route('/api/deadlines', methods=['GET'])
def get_deadlines():
    """Retrieve all deadlines."""
    today = date.today()
    return jsonify([_deadline_payload(d, today) for d in _deadlines])


@app.route('/api/deadlines/upcoming', methods=['GET'])
def get_upcoming_deadlines():
    """Return deadlines due within 7 days (plus overdue), sorted by due date."""
    today = date.today()
    result = []
    for d in _deadlines:
        p = _deadline_payload(d, today)
        if p["days_left"] is not None and p["days_left"] <= 7:
            result.append(p)
    result.sort(key=lambda x: x["due_date"])
    return jsonify(result)


@app.route('/api/deadlines', methods=['POST'])
def add_deadline():
    """Add a new deadline."""
    data = request.json or {}
    title    = (data.get("title") or "").strip()
    due_date = (data.get("due_date") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "Title is required."}), 400
    if not due_date:
        return jsonify({"success": False, "error": "Due date is required."}), 400
    try:
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "error": "Due date must be YYYY-MM-DD."}), 400

    d = Deadline(
        title=title,
        due_date=due_date,
        deadline_type=data.get("type", "assignment"),
        course=data.get("course", ""),
        description=data.get("description", ""),
        student_id=data.get("student_id") or None,
    )
    _deadlines.append(d)
    if not deadline_storage.save(_deadlines):
        _deadlines.pop()
        return jsonify({"success": False, "error": "Could not save deadline."}), 500
    return jsonify({"success": True, "deadline": _deadline_payload(d, date.today())})


@app.route('/api/deadlines/<deadline_id>', methods=['PUT'])
def update_deadline(deadline_id):
    """Update an existing deadline by its UUID."""
    d = next((x for x in _deadlines if x.id == deadline_id), None)
    if d is None:
        return jsonify({"success": False, "error": "Deadline not found."}), 404

    data     = request.json or {}
    title    = (data.get("title") or "").strip()
    due_date = (data.get("due_date") or "").strip()
    if not title:
        return jsonify({"success": False, "error": "Title is required."}), 400
    if not due_date:
        return jsonify({"success": False, "error": "Due date is required."}), 400
    try:
        datetime.strptime(due_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"success": False, "error": "Due date must be YYYY-MM-DD."}), 400

    # Snapshot for rollback
    old = d.to_dict()
    idx = _deadlines.index(d)
    _deadlines[idx] = Deadline(
        title=title,
        due_date=due_date,
        deadline_type=data.get("type", d.type),
        course=data.get("course", d.course),
        description=data.get("description", d.description),
        student_id=data.get("student_id") or None,
        deadline_id=deadline_id,
    )
    if not deadline_storage.save(_deadlines):
        _deadlines[idx] = Deadline.from_dict(old)
        return jsonify({"success": False, "error": "Could not save update."}), 500
    return jsonify({"success": True, "deadline": _deadline_payload(_deadlines[idx], date.today())})


@app.route('/api/deadlines/<deadline_id>', methods=['DELETE'])
def delete_deadline(deadline_id):
    """Delete a deadline by its UUID."""
    idx = next((i for i, x in enumerate(_deadlines) if x.id == deadline_id), None)
    if idx is None:
        return jsonify({"success": False, "error": "Deadline not found."}), 404
    removed = _deadlines.pop(idx)
    if not deadline_storage.save(_deadlines):
        _deadlines.insert(idx, removed)
        return jsonify({"success": False, "error": "Could not save deletion."}), 500
    return jsonify({"success": True})


# ---------------------------------------------------------------------------
# Seed — generate random students
# ---------------------------------------------------------------------------

_FIRST_NAMES = [
    "Alice", "Bob", "Carlos", "Diana", "Ethan", "Fiona", "George", "Hannah",
    "Ivan", "Julia", "Kevin", "Laura", "Marcus", "Nina", "Oscar", "Priya",
    "Quinn", "Rachel", "Samuel", "Tara", "Umar", "Violet", "William", "Xena",
    "Yusuf", "Zoe", "Aiden", "Bella", "Connor", "Daisy", "Eli", "Faith",
    "Gabe", "Holly", "Iris", "Jack", "Kira", "Liam", "Maya", "Noah",
    "Olivia", "Parker", "Ruby", "Sophia", "Tyler", "Uma", "Victor", "Wendy",
]
_LAST_NAMES = [
    "Smith", "Johnson", "Williams", "Brown", "Jones", "Garcia", "Miller",
    "Davis", "Rodriguez", "Martinez", "Hernandez", "Lopez", "Wilson", "Anderson",
    "Thomas", "Taylor", "Moore", "Jackson", "Martin", "Lee", "Perez", "Thompson",
    "White", "Harris", "Sanchez", "Clark", "Ramirez", "Lewis", "Robinson", "Walker",
    "Young", "Allen", "King", "Wright", "Scott", "Torres", "Nguyen", "Hill",
    "Flores", "Green", "Adams", "Nelson", "Baker", "Hall", "Rivera", "Campbell",
]
_MAJORS = [
    "Computer Science", "Mathematics", "Physics", "Engineering",
    "Business Administration", "Psychology", "Biology", "Chemistry",
    "Economics", "Political Science", "English Literature", "History",
    "Nursing", "Architecture", "Philosophy",
]
_YEARS = ["Freshman", "Sophomore", "Junior", "Senior", "Graduate"]
_DEPARTMENTS = [
    "Science & Technology", "Liberal Arts", "Business", "Health Sciences",
    "Engineering", "Social Sciences",
]
_COURSE_POOL = [
    "Calculus I", "Calculus II", "Linear Algebra", "Statistics",
    "Intro to Programming", "Data Structures", "Algorithms", "Operating Systems",
    "Databases", "Software Engineering", "Networking", "Machine Learning",
    "Physics I", "Chemistry I", "Biology I", "English Composition",
    "Technical Writing", "Ethics in Technology", "Economics 101", "Psychology 101",
]


@app.route('/api/seed', methods=['POST'])
def seed_students():
    """Generate n random students and add them to the roster.

    Body (JSON, all optional):
        n          int  Number of students to generate (1–100, default 10).
        clear      bool If true, remove all existing students first.

    Returns the list of newly added students.
    """
    data = request.json or {}

    # --- n ---
    n_raw = data.get("n", 10)
    try:
        n = int(n_raw)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "n must be an integer."}), 400
    if not (1 <= n <= 100):
        return jsonify({"success": False, "error": "n must be between 1 and 100."}), 400

    # --- clear ---
    clear = bool(data.get("clear", False))
    if clear:
        existing = manager.get_all_students()
        for i in range(len(existing) - 1, -1, -1):
            manager.remove_student(i)

    added = []
    used_names: set[str] = set()
    attempts = 0
    while len(added) < n and attempts < n * 5:
        attempts += 1
        first = random.choice(_FIRST_NAMES)
        last = random.choice(_LAST_NAMES)
        name = f"{first} {last}"
        if name in used_names:
            continue
        used_names.add(name)

        grade = round(random.uniform(40, 100), 1)
        major = random.choice(_MAJORS)
        year = random.choice(_YEARS)
        dept = random.choice(_DEPARTMENTS)
        email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@university.edu"

        # 1–3 random courses
        num_courses = random.randint(1, 3)
        course_names = random.sample(_COURSE_POOL, min(num_courses, len(_COURSE_POOL)))
        courses = [CourseGrade(course=c, grade=round(random.uniform(50, 100), 1)) for c in course_names]

        try:
            student = manager.add_student(
                name=name,
                grade=grade,
                email=email,
                major=major,
                academic_year=year,
                department=dept,
                courses=courses,
            )
            added.append(student)
        except ValueError:
            pass  # name conflict or validation error — skip

    if not _save_dataset():
        return jsonify({"success": False, "error": "Students generated but could not be saved."}), 503

    all_students = manager.get_all_students()
    id_to_idx = {s.id: i for i, s in enumerate(all_students)}
    return jsonify({
        "success": True,
        "added": len(added),
        "students": [student_to_payload(s, id_to_idx[s.id]) for s in added],
    })


# ---------------------------------------------------------------------------
# Seed — generate random classes
# ---------------------------------------------------------------------------

_CLASS_TEMPLATES = [
    ("CS101", "Introduction to Computer Science"),
    ("CS201", "Data Structures & Algorithms"),
    ("CS301", "Operating Systems"),
    ("CS401", "Software Engineering"),
    ("CS450", "Machine Learning"),
    ("CS460", "Computer Networks"),
    ("CS470", "Database Systems"),
    ("CS480", "Compiler Design"),
    ("MATH101", "Calculus I"),
    ("MATH102", "Calculus II"),
    ("MATH201", "Linear Algebra"),
    ("MATH301", "Probability & Statistics"),
    ("MATH401", "Discrete Mathematics"),
    ("PHYS101", "Physics I: Mechanics"),
    ("PHYS102", "Physics II: Electromagnetism"),
    ("CHEM101", "General Chemistry I"),
    ("CHEM201", "Organic Chemistry"),
    ("BIO101", "Introduction to Biology"),
    ("BIO301", "Genetics"),
    ("ENG101", "English Composition"),
    ("ENG201", "Technical Writing"),
    ("ENG301", "Literature & Society"),
    ("BUS101", "Introduction to Business"),
    ("BUS201", "Marketing Principles"),
    ("BUS301", "Financial Accounting"),
    ("BUS401", "Strategic Management"),
    ("ECON101", "Microeconomics"),
    ("ECON201", "Macroeconomics"),
    ("PSY101", "Introduction to Psychology"),
    ("PSY301", "Developmental Psychology"),
    ("SOC101", "Introduction to Sociology"),
    ("HIST101", "World History I"),
    ("HIST201", "American History"),
    ("PHIL101", "Introduction to Philosophy"),
    ("PHIL201", "Ethics"),
    ("ARCH101", "Architectural Design I"),
    ("ARCH201", "Structural Systems"),
    ("NUR101", "Foundations of Nursing"),
    ("NUR301", "Pharmacology"),
    ("ENVS101", "Environmental Science"),
    ("ENVS201", "Climate & Sustainability"),
    ("POLS101", "Introduction to Political Science"),
    ("POLS301", "International Relations"),
    ("STAT201", "Applied Statistics"),
    ("AI301", "Artificial Intelligence"),
    ("CYB201", "Cybersecurity Fundamentals"),
    ("WEB201", "Web Development"),
    ("PROJ401", "Capstone Project"),
    ("SEMINAR", "Research Methods Seminar"),
    ("ELEC101", "Electrical Engineering Basics"),
]
_CREDIT_OPTIONS = [1.0, 2.0, 3.0, 3.0, 3.0, 4.0]  # weighted toward 3 credits


@app.route('/api/seed/classes', methods=['POST'])
def seed_classes():
    """Generate n random classes.

    Body (JSON, all optional):
        n      int   Number of classes to generate (1–50, default 10).
        clear  bool  If true, delete all existing classes first (only those with no enrollments).

    Returns the list of newly added classes.
    """
    data = request.json or {}

    n_raw = data.get("n", 10)
    try:
        n = int(n_raw)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "n must be an integer."}), 400
    if not (1 <= n <= 50):
        return jsonify({"success": False, "error": "n must be between 1 and 50."}), 400

    clear = bool(data.get("clear", False))
    if clear:
        for cls in list(class_manager.get_all_classes()):
            try:
                class_manager.delete_class(cls.id)
            except ValueError:
                pass  # skip classes with enrollments

    from datetime import date as _date, timedelta as _td
    today = _date.today()

    # Pick n unique templates
    pool = list(_CLASS_TEMPLATES)
    random.shuffle(pool)
    templates = pool[:n]

    added = []
    for code, title in templates:
        credits = random.choice(_CREDIT_OPTIONS)
        # Randomise term: either current or next semester (roughly 4-month windows)
        offset_months = random.choice([0, 4, 8])
        term_start = today.replace(day=1) + _td(days=offset_months * 30)
        term_end = term_start + _td(days=random.randint(90, 120))
        try:
            record = class_manager.add_class(
                code=code,
                title=title,
                credits=credits,
                term_start=term_start,
                term_end=term_end,
            )
            added.append(record)
        except ValueError:
            pass  # duplicate code or invalid — skip

    if not _save_dataset():
        return jsonify({"success": False, "error": "Classes generated but could not be saved."}), 503

    return jsonify({
        "success": True,
        "added": len(added),
        "classes": [_class_payload(c) for c in added],
    })


# ---------------------------------------------------------------------------
# Seed — generate random deadlines
# ---------------------------------------------------------------------------

_DEADLINE_TEMPLATES = {
    "assignment": [
        "Problem Set {n}", "Homework {n}", "Lab Report {n}", "Reading Response {n}",
        "Case Study {n}", "Weekly Journal {n}", "Programming Assignment {n}",
        "Data Analysis {n}", "Research Summary {n}", "Worksheet {n}",
    ],
    "exam": [
        "Midterm Exam", "Final Exam", "Quiz {n}", "In-Class Test {n}",
        "Practical Exam", "Oral Examination", "Online Assessment {n}",
    ],
    "project": [
        "Group Project Proposal", "Final Project Submission", "Project Milestone {n}",
        "Capstone Presentation", "Design Prototype", "Research Paper",
        "Portfolio Submission", "Team Deliverable {n}",
    ],
    "other": [
        "Course Withdrawal Deadline", "Grade Appeal Deadline",
        "Scholarship Application", "Internship Application Deadline",
        "Peer Review Submission", "Self-Evaluation Form",
    ],
}


@app.route('/api/seed/deadlines', methods=['POST'])
def seed_deadlines():
    """Generate n random deadlines spread across the next 90 days.

    Body (JSON, all optional):
        n      int   Number of deadlines to generate (1–100, default 10).
        clear  bool  If true, remove all existing deadlines first.

    Returns the list of newly added deadlines.
    """
    data = request.json or {}

    n_raw = data.get("n", 10)
    try:
        n = int(n_raw)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "n must be an integer."}), 400
    if not (1 <= n <= 100):
        return jsonify({"success": False, "error": "n must be between 1 and 100."}), 400

    clear = bool(data.get("clear", False))
    if clear:
        _deadlines.clear()

    from datetime import date as _date, timedelta as _td
    today = _date.today()

    # Weighted type distribution: more assignments, fewer exams/projects
    types = (
        ["assignment"] * 5 + ["exam"] * 2 + ["project"] * 2 + ["other"] * 1
    )

    # Use existing class codes as course names if available
    existing_codes = [c.code for c in class_manager.get_all_classes()]
    if not existing_codes:
        existing_codes = list(set(code for code, _ in _CLASS_TEMPLATES[:15]))

    added = []
    for i in range(n):
        d_type = random.choice(types)
        templates = _DEADLINE_TEMPLATES[d_type]
        title_template = random.choice(templates)
        title = title_template.replace("{n}", str(random.randint(1, 9)))
        course = random.choice(existing_codes)
        days_ahead = random.randint(-7, 90)   # some overdue, most upcoming
        due = today + _td(days=days_ahead)

        dl = Deadline(
            title=title,
            due_date=due.isoformat(),
            deadline_type=d_type,
            course=course,
            description="",
        )
        _deadlines.append(dl)
        added.append(dl)

    if not deadline_storage.save(_deadlines):
        # Roll back added entries
        for dl in added:
            if dl in _deadlines:
                _deadlines.remove(dl)
        return jsonify({"success": False, "error": "Deadlines generated but could not be saved."}), 503

    today_date = date.today()
    return jsonify({
        "success": True,
        "added": len(added),
        "deadlines": [_deadline_payload(d, today_date) for d in added],
    })


# ---------------------------------------------------------------------------
# PostgreSQL connection UI — local-demo mode only
# ---------------------------------------------------------------------------

def _is_loopback(req) -> bool:
    """Return True only when the request originated from localhost/127.0.0.1/::1."""
    remote = req.remote_addr or ""
    return remote in ("127.0.0.1", "::1", "localhost")


if LOCAL_DEMO_MODE:

    @app.route('/api/pg/test', methods=['POST'])
    def pg_test():
        """Test a PostgreSQL URL without creating schemas, migrating data, or switching
        the active backend.

        Body: {"url": "postgresql://..."}
        The URL is used only for the duration of this request and never logged.

        Returns:
            {"success": true}  on a successful connection ping.
            {"success": false, "error": "<safe message>"}  on failure.
        """
        if not _is_loopback(request):
            return jsonify({"success": False, "error": "Not available on this binding."}), 403

        data = request.json
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400
        url = data.get("url")
        if not isinstance(url, str) or not url.strip():
            return jsonify({"success": False, "error": "url is required."}), 400
        url = url.strip()

        # Validate that it looks like a PostgreSQL URL (no arbitrary SQL injection path)
        if not (url.startswith("postgresql://") or url.startswith("postgres://")):
            return jsonify({"success": False, "error": "url must start with postgresql:// or postgres://."}), 400

        try:
            from app.storage.postgres_storage import PostgresStorage, _add_connect_timeout, _redact
            import psycopg2
            dsn = _add_connect_timeout(url, 5)
            conn = psycopg2.connect(dsn)
            conn.close()
            return jsonify({"success": True})
        except ImportError:
            return jsonify({"success": False, "error": "psycopg2 is not installed."}), 503
        except Exception as exc:
            from app.storage.postgres_storage import _redact
            safe = _redact(str(exc))
            return jsonify({"success": False, "error": safe}), 503

    @app.route('/api/pg/connect', methods=['POST'])
    def pg_connect():
        """Switch the active backend to PostgreSQL.

        The schema must already exist (run setup_schema separately).
        The DATABASE_URL for restarts should be set in the environment, not stored here.
        Failed connection keeps the previous backend unchanged.

        Body: {"url": "postgresql://..."}
        The URL is held in process memory only — never returned, logged, or stored
        in browser storage, committed files, or URL query strings.

        Returns:
            {"success": true, "backend": "postgres"}  on switch.
            {"success": false, "error": "<safe message>"}  on failure.
        """
        if not _is_loopback(request):
            return jsonify({"success": False, "error": "Not available on this binding."}), 403

        data = request.json
        if not isinstance(data, dict):
            return jsonify({"success": False, "error": "Request body must be a JSON object."}), 400
        url = data.get("url")
        if not isinstance(url, str) or not url.strip():
            return jsonify({"success": False, "error": "url is required."}), 400
        url = url.strip()

        if not (url.startswith("postgresql://") or url.startswith("postgres://")):
            return jsonify({"success": False, "error": "url must start with postgresql:// or postgres://."}), 400

        try:
            from app.storage.postgres_storage import PostgresStorage
            new_storage = PostgresStorage(url, connect_timeout=5)
            manager.set_storage(new_storage)
            # Reload full dataset from the new backend
            _ds = new_storage.load_dataset()
            with manager._lock:
                manager._students = _ds.students
            class_manager.load_from_data(_ds.classes, _ds.enrollments)
            return jsonify({"success": True, "backend": "postgres"})
        except ImportError:
            return jsonify({"success": False, "error": "psycopg2 is not installed."}), 503
        except Exception as exc:
            from app.storage.postgres_storage import _redact
            safe = _redact(str(exc))
            return jsonify({"success": False, "error": safe}), 503


if __name__ == '__main__':
    print("Starting Student Grade Management System Web Dashboard...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
