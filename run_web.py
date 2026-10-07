import os
from flask import Flask, jsonify, request, render_template

from app.storage.json_storage import JsonStorage
from app.services.student_manager import StudentManager
from app.services.statistics_service import StatisticsService
from app.models.student import Student, CourseGrade
from app.config import MIN_GRADE, MAX_GRADE

# Set directories relative to this file
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Initialize Storage & StudentManager
storage = JsonStorage()
manager = StudentManager(storage)
manager.load()


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
    }


# ---------------------------------------------------------------------------
# Config & root
# ---------------------------------------------------------------------------

@app.route('/api/config', methods=['GET'])
def get_config():
    """Expose grade boundary constants so the frontend stays in sync with config.py."""
    return jsonify({"min_grade": MIN_GRADE, "max_grade": MAX_GRADE})


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


@app.route('/api/students', methods=['POST'])
def add_student():
    """Add a new student with validation."""
    data = request.json or {}
    name = data.get("name", "").strip()
    grade = data.get("grade")

    if grade is None:
        return jsonify({"success": False, "error": "Grade is required."}), 400

    try:
        grade_val = float(grade)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Grade must be a number."}), 400

    # Parse optional courses list
    raw_courses = data.get("courses") or []
    courses = []
    for c in raw_courses:
        try:
            courses.append(CourseGrade.from_dict(c))
        except (KeyError, ValueError) as e:
            return jsonify({"success": False, "error": f"Invalid course entry: {e}"}), 400

    # Optional GPA
    gpa = None
    if data.get("gpa") not in (None, ""):
        try:
            gpa = float(data["gpa"])
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "GPA must be a number."}), 400

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
        )
        manager.save()
        students = manager.get_all_students()
        idx = next(i for i, s in enumerate(students) if s.id == student.id)
        return jsonify({"success": True, "student": student_to_payload(student, idx)})
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/students/<student_id>', methods=['PUT'])
def update_student(student_id):
    """Update a student's fields identified by their stable UUID.

    Accepts a partial update — only fields present in the JSON body are changed.
    """
    data = request.json or {}

    # Build kwargs for update_student; convert types where needed.
    fields = {}

    if "grade" in data:
        try:
            fields["grade"] = float(data["grade"])
        except (ValueError, TypeError):
            return jsonify({"success": False, "error": "Grade must be a number."}), 400

    if "email" in data:
        fields["email"] = str(data["email"])
    if "major" in data:
        fields["major"] = str(data["major"])
    if "academic_year" in data:
        fields["academic_year"] = str(data["academic_year"])
    if "notes" in data:
        fields["notes"] = str(data["notes"])

    if "gpa" in data:
        if data["gpa"] in (None, ""):
            fields["gpa"] = None
        else:
            try:
                fields["gpa"] = float(data["gpa"])
            except (ValueError, TypeError):
                return jsonify({"success": False, "error": "GPA must be a number."}), 400

    if "courses" in data:
        raw_courses = data["courses"] or []
        courses = []
        for c in raw_courses:
            try:
                courses.append(CourseGrade.from_dict(c))
            except (KeyError, ValueError) as e:
                return jsonify({"success": False, "error": f"Invalid course entry: {e}"}), 400
        fields["courses"] = courses

    if not fields:
        return jsonify({"success": False, "error": "No fields to update."}), 400

    try:
        student = manager.update_student(student_id, **fields)
        manager.save()
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
        manager.save()
        return jsonify({
            "success": True,
            "student": {"name": student.name, "grade": student.grade}
        })
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
    })


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
    manager.save()
    students = manager.get_all_students()
    return jsonify([student_to_payload(s, i) for i, s in enumerate(students)])


@app.route('/api/save', methods=['POST'])
def save_data():
    """Save data to the persistence layer."""
    success = manager.save()
    return jsonify({"success": success})


if __name__ == '__main__':
    print("Starting Student Grade Management System Web Dashboard...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
