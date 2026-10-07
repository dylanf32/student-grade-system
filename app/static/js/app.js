/* ==========================================================================
   Student Grade Management System — Frontend Controller
   ========================================================================== */

const API = {
    students: '/api/students',
    stats: '/api/stats',
    search: '/api/search',
    sort: '/api/sort',
    save: '/api/save',
};

/* ==========================================================================
   TOAST NOTIFICATION SYSTEM
   ========================================================================== */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    const toast = document.createElement('div');

    const iconMap = {
        success: 'fa-circle-check',
        error: 'fa-circle-exclamation',
        info: 'fa-circle-info',
    };

    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid ${iconMap[type] || iconMap.info}"></i> ${message}`;
    container.appendChild(toast);

    // Auto-remove after animation completes
    setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 5000);
}

/* ==========================================================================
   GRADE STATUS HELPERS
   ========================================================================== */
function getGradeStatus(grade) {
    // Thresholds mirror app/config.py: 90 Excellent, 80 Good, 70 Average, 60 Below Avg, <60 Failing
    if (grade >= 90) return { label: 'Excellent',    badge: 'badge-excellent',  icon: '🌟' };
    if (grade >= 80) return { label: 'Good',         badge: 'badge-good',       icon: '👍' };
    if (grade >= 70) return { label: 'Average',      badge: 'badge-average',    icon: '📘' };
    if (grade >= 60) return { label: 'Below Avg',    badge: 'badge-below-avg',  icon: '⚠️' };
    return           { label: 'Failing',             badge: 'badge-failing',    icon: '❌' };
}

function getGradeColor(grade) {
    if (grade >= 90) return 'var(--success)';
    if (grade >= 80) return 'var(--info)';
    if (grade >= 70) return 'var(--average)';
    if (grade >= 60) return 'var(--warning)';
    return 'var(--danger)';
}

/* ==========================================================================
   FETCH & RENDER: STUDENTS TABLE
   ========================================================================== */
async function loadStudents() {
    try {
        const res = await fetch(API.students);
        const students = await res.json();
        renderStudentTable(students);
        loadStats();
    } catch (err) {
        showToast('Failed to load students.', 'error');
    }
}

function renderStudentTable(students) {
    const tbody = document.getElementById('students-table-body');
    const subtitle = document.getElementById('table-subtitle');

    if (!students || students.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="6" class="table-loading" style="color: var(--text-dim);">
                    <i class="fa-solid fa-inbox" style="font-size:2rem; display:block; margin-bottom:0.75rem; opacity:0.3;"></i>
                    No students found. Add your first student using the form.
                </td>
            </tr>`;
        subtitle.textContent = '0 records in database';
        return;
    }

    subtitle.textContent = `Displaying ${students.length} record(s)`;

    // Build rows as DOM nodes so no user-supplied value is ever interpolated
    // into an attribute or event-handler string (XSS prevention).
    tbody.innerHTML = '';
    students.forEach(s => {
        const status = getGradeStatus(s.grade);
        const gradeColor = getGradeColor(s.grade);

        const tr = document.createElement('tr');
        tr.dataset.index = s.index;
        tr.dataset.studentId = s.student_id;

        tr.innerHTML = `
            <td class="index-cell">${s.index}</td>
            <td class="id-cell">${escapeHtml(s.id)}</td>
            <td class="name-cell">${escapeHtml(s.name)}</td>
            <td class="grade-cell" style="color: ${gradeColor};">${s.grade}</td>
            <td><span class="badge ${status.badge}">${status.icon} ${status.label}</span></td>
            <td class="text-right">
                <div class="actions-cell">
                    <button class="btn-action btn-action-edit" title="Edit Grade">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                    <button class="btn-action btn-action-delete" title="Delete Student">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </td>`;

        // Attach handlers via addEventListener — no string interpolation into
        // event attributes, so malicious names cannot inject JS.
        tr.querySelector('.btn-action-edit').addEventListener('click', () => {
            openEditModal(s.student_id, s.name, s.id, s.grade);
        });
        tr.querySelector('.btn-action-delete').addEventListener('click', () => {
            deleteStudent(s.student_id, s.name);
        });

        tbody.appendChild(tr);
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

/* ==========================================================================
   FETCH & RENDER: STATISTICS
   ========================================================================== */
async function loadStats() {
    try {
        const res = await fetch(API.stats);
        const stats = await res.json();

        document.getElementById('stat-total').textContent = stats.total_students;
        document.getElementById('stat-average').textContent = stats.average;
        document.getElementById('stat-highest').textContent = stats.highest;
        document.getElementById('stat-lowest').textContent = stats.lowest;
        document.getElementById('stat-pass-rate').textContent = stats.passing_rate + '%';
    } catch (err) {
        // silently fail stats, table is more important
    }
}

/* ==========================================================================
   ADD STUDENT
   ========================================================================== */
document.getElementById('add-student-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    const nameInput = document.getElementById('student-name');
    const gradeInput = document.getElementById('student-grade');
    const name = nameInput.value.trim();
    const grade = gradeInput.value;

    if (!name) {
        showToast('Please enter a student name.', 'error');
        nameInput.focus();
        return;
    }
    if (grade === '' || isNaN(grade) || Number(grade) < 0 || Number(grade) > 100) {
        showToast('Grade must be a number between 0 and 100.', 'error');
        gradeInput.focus();
        return;
    }

    try {
        const res = await fetch(API.students, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, grade: Number(grade) }),
        });
        const data = await res.json();

        if (data.success) {
            showToast(`✅ ${data.student.name} added with grade ${data.student.grade}`, 'success');
            nameInput.value = '';
            gradeInput.value = '';
            nameInput.focus();
            loadStudents();
        } else {
            showToast(data.error || 'Failed to add student.', 'error');
        }
    } catch (err) {
        showToast('Network error. Could not add student.', 'error');
    }
});

/* ==========================================================================
   DELETE STUDENT
   ========================================================================== */
async function deleteStudent(studentId, name) {
    if (!confirm(`Are you sure you want to remove "${name}"?`)) return;

    try {
        const res = await fetch(`${API.students}/${studentId}`, { method: 'DELETE' });
        const data = await res.json();

        if (data.success) {
            showToast(`🗑️ ${data.student.name} has been removed.`, 'success');
            loadStudents();
        } else {
            showToast(data.error || 'Failed to delete student.', 'error');
        }
    } catch (err) {
        showToast('Network error. Could not delete student.', 'error');
    }
}

/* ==========================================================================
   EDIT GRADE MODAL
   ========================================================================== */
const editModal = document.getElementById('edit-modal');
const editForm = document.getElementById('edit-grade-form');
const editIdInput = document.getElementById('edit-student-id');
const editGradeInput = document.getElementById('edit-student-grade');
const modalNameEl = document.getElementById('modal-student-name');
const modalIdEl = document.getElementById('modal-student-id');

function openEditModal(studentId, name, displayId, currentGrade) {
    editIdInput.value = studentId;  // store UUID, not position
    editGradeInput.value = currentGrade;
    modalNameEl.textContent = name;
    modalIdEl.textContent = displayId;
    editModal.classList.remove('hidden');
    editGradeInput.focus();
    editGradeInput.select();
}

function closeEditModal() {
    editModal.classList.add('hidden');
}

document.getElementById('modal-close').addEventListener('click', closeEditModal);
document.getElementById('btn-edit-cancel').addEventListener('click', closeEditModal);

// Close modal on overlay click
editModal.addEventListener('click', (e) => {
    if (e.target === editModal) closeEditModal();
});

// Close modal on Escape key
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && !editModal.classList.contains('hidden')) {
        closeEditModal();
    }
});

editForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const studentId = editIdInput.value;  // UUID, not positional index
    const newGrade = editGradeInput.value;

    if (newGrade === '' || isNaN(newGrade) || Number(newGrade) < 0 || Number(newGrade) > 100) {
        showToast('Grade must be between 0 and 100.', 'error');
        editGradeInput.focus();
        return;
    }

    try {
        const res = await fetch(`${API.students}/${studentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ grade: Number(newGrade) }),
        });
        const data = await res.json();

        if (data.success) {
            showToast(`✏️ ${data.student.name}'s grade updated to ${data.student.grade}`, 'success');
            closeEditModal();
            loadStudents();
        } else {
            showToast(data.error || 'Failed to update grade.', 'error');
        }
    } catch (err) {
        showToast('Network error. Could not update grade.', 'error');
    }
});

/* ==========================================================================
   SEARCH STUDENT
   ========================================================================== */
let searchDebounce = null;
const searchInput = document.getElementById('search-input');
const searchResultContainer = document.getElementById('search-result-container');

searchInput.addEventListener('input', () => {
    clearTimeout(searchDebounce);
    const query = searchInput.value.trim();

    if (!query) {
        searchResultContainer.classList.add('hidden');
        clearHighlight();
        return;
    }

    searchDebounce = setTimeout(() => performSearch(query), 350);
});

async function performSearch(query) {
    try {
        const res = await fetch(`${API.search}?name=${encodeURIComponent(query)}`);
        const data = await res.json();

        if (data.found) {
            // data.students contains all matches (may be > 1 for duplicate names).
            const students = data.students;
            const first = students[0];

            // Update the visible result card with the first match summary.
            document.getElementById('result-name').textContent = first.name;
            document.getElementById('result-id').textContent = first.id;
            document.getElementById('result-grade').textContent =
                students.length === 1
                    ? `Grade: ${first.grade}`
                    : `${students.length} matches — grades: ${students.map(s => s.grade).join(', ')}`;
            searchResultContainer.classList.remove('hidden');

            // Highlight every matching row in the table.
            clearHighlight();
            students.forEach(s => highlightRow(s.index));
        } else {
            searchResultContainer.classList.add('hidden');
            clearHighlight();
        }
    } catch (err) {
        // silently fail
    }
}

function highlightRow(index) {
    const row = document.querySelector(`tr[data-index="${index}"]`);
    if (row) {
        row.classList.add('row-highlight');
        row.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
}

function clearHighlight() {
    document.querySelectorAll('.row-highlight').forEach(r => r.classList.remove('row-highlight'));
}

document.getElementById('btn-search-locate').addEventListener('click', () => {
    clearHighlight();
    const name = document.getElementById('result-name').textContent;
    const rows = document.querySelectorAll('#students-table-body tr');
    rows.forEach(row => {
        const nameCell = row.querySelector('.name-cell');
        if (nameCell && nameCell.textContent === name) {
            row.scrollIntoView({ behavior: 'smooth', block: 'center' });
            row.classList.add('row-highlight');
        }
    });
});

document.getElementById('btn-search-clear').addEventListener('click', () => {
    searchInput.value = '';
    searchResultContainer.classList.add('hidden');
    clearHighlight();
});

/* ==========================================================================
   SORT STUDENTS
   ========================================================================== */
document.getElementById('btn-sort-asc').addEventListener('click', () => sortStudents(true));
document.getElementById('btn-sort-desc').addEventListener('click', () => sortStudents(false));

async function sortStudents(ascending) {
    try {
        const res = await fetch(`${API.sort}?ascending=${ascending}`);
        const students = await res.json();
        renderStudentTable(students);
        loadStats();
        showToast(`🔃 Sorted by grade (${ascending ? 'Low → High' : 'High → Low'})`, 'info');
    } catch (err) {
        showToast('Failed to sort students.', 'error');
    }
}

/* ==========================================================================
   SAVE DATABASE
   ========================================================================== */
document.getElementById('btn-save-db').addEventListener('click', async () => {
    try {
        const res = await fetch(API.save, { method: 'POST' });
        const data = await res.json();

        if (data.success) {
            showToast('💾 Database saved successfully!', 'success');
        } else {
            showToast('Failed to save database.', 'error');
        }
    } catch (err) {
        showToast('Network error. Could not save.', 'error');
    }
});

/* ==========================================================================
   INITIAL LOAD
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
    loadStudents();
});
