import os
from flask import Flask, jsonify, request, render_template

from app.storage.json_storage import JsonStorage
from app.services.student_manager import StudentManager
from app.services.statistics_service import StatisticsService
from app.models.student import Student

# Set directories relative to this file
template_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'templates'))
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), 'app', 'static'))

app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)

# Initialize Storage & StudentManager
storage = JsonStorage()
manager = StudentManager(storage)
manager.load()

@app.route('/')
def index():
    """Serve the web application dashboard."""
    return render_template('index.html')

@app.route('/api/students', methods=['GET'])
def get_students():
    """Retrieve all students with their absolute indices and stable UUIDs."""
    students = manager.get_all_students()
    return jsonify([
        {
            "index": i,
            "student_id": s.id,
            "id": f"STU-{i+1:03d}",
            "name": s.name,
            "grade": s.grade
        }
        for i, s in enumerate(students)
    ])

@app.route('/api/students', methods=['POST'])
def add_student():
    """Add a new student with validation."""
    data = request.json or {}
    name = data.get("name", "").strip()
    grade = data.get("grade")
    
    if grade is None:
        return jsonify({"success": False, "error": "Grade is required."}), 400
        
    try:
        # grade must be numeric
        grade_val = float(grade)
        # if integer representation is identical (e.g. 85.0), make it integer
        if grade_val.is_integer():
            grade_val = int(grade_val)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Grade must be a number."}), 400

    try:
        student = manager.add_student(name, grade_val)
        manager.save()
        return jsonify({
            "success": True,
            "student": {"student_id": student.id, "name": student.name, "grade": student.grade}
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400

@app.route('/api/students/<student_id>', methods=['PUT'])
def update_student(student_id):
    """Update a student's grade identified by their stable UUID."""
    data = request.json or {}
    new_grade = data.get("grade")
    
    if new_grade is None:
        return jsonify({"success": False, "error": "New grade is required."}), 400
        
    try:
        grade_val = float(new_grade)
        if grade_val.is_integer():
            grade_val = int(grade_val)
    except (ValueError, TypeError):
        return jsonify({"success": False, "error": "Grade must be a number."}), 400

    # Find the student by stable UUID, not by list position.
    students = manager.get_all_students()
    index = next((i for i, s in enumerate(students) if s.id == student_id), None)
    if index is None:
        return jsonify({"success": False, "error": "Student not found."}), 404

    try:
        student = manager.update_grade(index, grade_val)
        manager.save()
        return jsonify({
            "success": True,
            "student": {"student_id": student.id, "name": student.name, "grade": student.grade}
        })
    except ValueError as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route('/api/students/<student_id>', methods=['DELETE'])
def delete_student(student_id):
    """Delete a student identified by their stable UUID.

    Using UUID instead of list position means that deleting one student
    never changes the identity of any other student, and a stale request
    for an already-deleted ID returns 404 rather than silently deleting
    the wrong person.
    """
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

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Retrieve current grade statistics."""
    students = manager.get_all_students()
    stats = StatisticsService.compute(students)
    
    # Calculate passing rate
    passing_rate = round((stats.passing_count / stats.total_students * 100), 1) if stats.total_students > 0 else 0.0
    
    return jsonify({
        "total_students": stats.total_students,
        "average": stats.average,
        "highest": stats.highest,
        "lowest": stats.lowest,
        "passing_count": stats.passing_count,
        "failing_count": stats.failing_count,
        "passing_rate": passing_rate
    })

@app.route('/api/search', methods=['GET'])
def search_student():
    """Search for a student by name (case-insensitive)."""
    name = request.args.get("name", "").strip()
    if not name:
        return jsonify({"success": False, "error": "Name query parameter is required."}), 400
        
    index = manager.search_by_name(name)
    if index != -1:
        s = manager.get_student(index)
        return jsonify({
            "found": True,
            "index": index,
            "student": {
                "index": index,
                "student_id": s.id,
                "id": f"STU-{index+1:03d}",
                "name": s.name,
                "grade": s.grade
            }
        })
    return jsonify({"found": False})

@app.route('/api/sort', methods=['GET'])
def sort_students():
    """Sort students by grade in-place and return the sorted list."""
    ascending = request.args.get("ascending", "true").lower() == "true"
    manager.sort_by_grade(ascending)
    manager.save()
    
    # Return sorted list with stable UUIDs
    students = manager.get_all_students()
    return jsonify([
        {
            "index": i,
            "student_id": s.id,
            "id": f"STU-{i+1:03d}",
            "name": s.name,
            "grade": s.grade
        }
        for i, s in enumerate(students)
    ])

@app.route('/api/save', methods=['POST'])
def save_data():
    """Save data to the persistence layer."""
    success = manager.save()
    return jsonify({"success": success})

if __name__ == '__main__':
    print("Starting Student Grade Management System Web Dashboard...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
