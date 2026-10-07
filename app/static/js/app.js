/* ==========================================================================
   Student Grade Management System — Frontend Controller
   ========================================================================== */

const API = {
    students: '/api/students',
    stats:    '/api/stats',
    search:   '/api/search',
    filter:   '/api/filter',
    sort:     '/api/sort',
    save:     '/api/save',
    config:   '/api/config',
};

// Grade bounds — updated from /api/config on load; defaults match config.py.
let minGrade = 0;
let maxGrade = 100;

/* ==========================================================================
   TOAST NOTIFICATION SYSTEM
   ========================================================================== */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) { console.warn('Missing element: toast-container'); return; }
    const toast = document.createElement('div');
    const iconMap = {
        success: 'fa-circle-check',
        error:   'fa-circle-exclamation',
        info:    'fa-circle-info',
    };
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid ${iconMap[type] || iconMap.info}"></i> ${message}`;
    container.appendChild(toast);
    const timerId = setTimeout(() => {
        clearTimeout(timerId);
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 5000);
    toast.dataset.timerId = timerId;
}

/* ==========================================================================
   GRADE / STANDING HELPERS
   ========================================================================== */
function getGradeStatus(grade) {
    if (grade >= 90) return { label: 'Excellent',  badge: 'badge-excellent',  icon: '🌟' };
    if (grade >= 80) return { label: 'Good',        badge: 'badge-good',       icon: '👍' };
    if (grade >= 70) return { label: 'Average',     badge: 'badge-average',    icon: '📘' };
    if (grade >= 60) return { label: 'Below Avg',   badge: 'badge-below-avg',  icon: '⚠️' };
    return           { label: 'Failing',            badge: 'badge-failing',    icon: '❌' };
}

function getGradeColor(grade) {
    if (grade >= 90) return 'var(--success)';
    if (grade >= 80) return 'var(--info)';
    if (grade >= 70) return 'var(--average)';
    if (grade >= 60) return 'var(--warning)';
    return 'var(--danger)';
}

function getStandingBadgeClass(standing) {
    if (!standing) return 'badge-satisfactory';
    const s = standing.toLowerCase();
    if (s.includes("dean")) return 'badge-deans-list';
    if (s.includes("good")) return 'badge-good-standing';
    if (s.includes("satisf")) return 'badge-satisfactory';
    if (s.includes("warning")) return 'badge-warning';
    return 'badge-probation';
}

function getGpaColor(gpa) {
    if (gpa == null) return 'var(--text-muted)';
    if (gpa >= 3.5) return 'var(--success)';
    if (gpa >= 3.0) return 'var(--info)';
    if (gpa >= 2.0) return 'var(--average)';
    if (gpa >= 1.0) return 'var(--warning)';
    return 'var(--danger)';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.appendChild(document.createTextNode(text));
    return div.innerHTML;
}

/* ==========================================================================
   FETCH & RENDER: STUDENTS TABLE
   ========================================================================== */
async function loadStudents() {
    try {
        const res = await fetch(API.students);
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const students = await res.json();
        renderStudentTable(students);
        loadStats();
    } catch (err) {
        showToast('Failed to load students.', 'error');
    }
}

function renderStudentTable(students) {
    const tbody    = document.getElementById('students-table-body');
    const subtitle = document.getElementById('table-subtitle');
    if (!tbody || !subtitle) { console.warn('Missing table elements'); return; }

    if (!students || students.length === 0) {
        tbody.innerHTML = `
            <tr>
                <td colspan="9" class="table-loading" style="color:var(--text-dim);">
                    <i class="fa-solid fa-inbox" style="font-size:2rem;display:block;margin-bottom:0.75rem;opacity:0.3;"></i>
                    No students found. Add your first student using the form.
                </td>
            </tr>`;
        subtitle.textContent = '0 records';
        return;
    }

    subtitle.textContent = `Displaying ${students.length} record(s)`;
    tbody.innerHTML = '';

    students.forEach(s => {
        const status      = getGradeStatus(s.grade);
        const gradeColor  = getGradeColor(s.grade);
        const gpaColor    = getGpaColor(s.gpa);
        const gpaDisplay  = (s.gpa != null) ? s.gpa.toFixed(2) : '—';
        const standingBadge = getStandingBadgeClass(s.standing);

        const tr = document.createElement('tr');
        tr.dataset.index     = s.index;
        tr.dataset.studentId = s.student_id;

        tr.innerHTML = `
            <td class="index-cell">${s.index + 1}</td>
            <td class="id-cell">${escapeHtml(s.id)}</td>
            <td class="name-cell">
                ${escapeHtml(s.name)}
                ${s.email ? `<span class="name-subtext">${escapeHtml(s.email)}</span>` : ''}
            </td>
            <td style="color:var(--text-muted);font-size:0.875rem;">${s.major ? escapeHtml(s.major) : '<span style="color:var(--text-dim)">—</span>'}</td>
            <td style="color:var(--text-muted);font-size:0.875rem;">${s.academic_year ? escapeHtml(s.academic_year) : '<span style="color:var(--text-dim)">—</span>'}</td>
            <td class="grade-cell" style="color:${gradeColor};">${s.grade}</td>
            <td><span class="gpa-pill" style="color:${gpaColor};">${gpaDisplay}</span></td>
            <td><span class="badge ${standingBadge}">${s.standing || '—'}</span></td>
            <td class="text-right">
                <div class="actions-cell">
                    <button class="btn-action btn-action-view" title="View Profile">
                        <i class="fa-solid fa-eye"></i>
                    </button>
                    <button class="btn-action btn-action-edit" title="Edit Record">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                    <button class="btn-action btn-action-delete" title="Delete Student">
                        <i class="fa-solid fa-trash-can"></i>
                    </button>
                </div>
            </td>`;

        tr.querySelector('.btn-action-view').addEventListener('click',   () => openDetailModal(s));
        tr.querySelector('.btn-action-edit').addEventListener('click',   () => openEditModal(s));
        tr.querySelector('.btn-action-delete').addEventListener('click', () => deleteStudent(s.student_id, s.name));

        tbody.appendChild(tr);
    });
}

/* ==========================================================================
   FETCH & RENDER: STATISTICS
   ========================================================================== */
async function loadStats() {
    try {
        const res = await fetch(API.stats);
        if (!res.ok) { console.warn(`Stats error: ${res.status}`); return; }
        const stats = await res.json();

        setTextIfExists('stat-total',    stats.total_students);
        setTextIfExists('stat-average',  stats.average);
        setTextIfExists('stat-highest',  stats.highest);
        setTextIfExists('stat-pass-rate', stats.passing_rate + '%');
        setTextIfExists('stat-avg-gpa',  stats.avg_gpa != null ? stats.avg_gpa.toFixed(2) : '—');
    } catch (err) {
        // silently fail
    }
}

function setTextIfExists(id, value) {
    const el = document.getElementById(id);
    if (!el) { console.warn(`Missing element: ${id}`); return; }
    el.textContent = (value == null) ? '—' : value;
}

/* ==========================================================================
   COURSE ENTRY HELPERS
   ========================================================================== */
function addCourseEntry(container, courseName = '', courseGrade = '') {
    const row = document.createElement('div');
    row.className = 'course-entry';
    row.innerHTML = `
        <input type="text" class="course-name-input" placeholder="Course name" value="${escapeHtml(courseName)}">
        <input type="number" class="course-grade-input" placeholder="Grade" min="0" max="100" value="${courseGrade !== '' && courseGrade != null ? courseGrade : ''}">
        <button type="button" class="btn-remove-course" title="Remove"><i class="fa-solid fa-xmark"></i></button>`;
    row.querySelector('.btn-remove-course').addEventListener('click', () => row.remove());
    container.appendChild(row);
}

function collectCourses(container) {
    const entries = container.querySelectorAll('.course-entry');
    const courses = [];
    for (const entry of entries) {
        const name  = entry.querySelector('.course-name-input').value.trim();
        const grade = entry.querySelector('.course-grade-input').value.trim();
        if (!name) continue;
        courses.push({
            course: name,
            grade:  grade !== '' ? parseFloat(grade) : null,
        });
    }
    return courses;
}

/* ==========================================================================
   ADD STUDENT
   ========================================================================== */
async function submitAddStudent(e) {
    e.preventDefault();

    const nameInput  = document.getElementById('student-name');
    const gradeInput = document.getElementById('student-grade');
    const emailInput = document.getElementById('student-email');
    const majorInput = document.getElementById('student-major');
    const yearInput  = document.getElementById('student-year');
    const gpaInput   = document.getElementById('student-gpa');
    const notesInput = document.getElementById('student-notes');
    const coursesCtn = document.getElementById('add-courses-list');

    if (!nameInput || !gradeInput) { console.warn('Missing add-student form inputs'); return; }

    const name  = nameInput.value.trim();
    const grade = gradeInput.value;

    if (!name || name.length < 2) {
        showToast('Name must be at least 2 characters.', 'error');
        nameInput.focus();
        return;
    }
    if (grade === '' || isNaN(grade) || Number(grade) < minGrade || Number(grade) > maxGrade) {
        showToast(`Grade must be between ${minGrade} and ${maxGrade}.`, 'error');
        gradeInput.focus();
        return;
    }

    const gpaVal = gpaInput && gpaInput.value.trim() !== '' ? parseFloat(gpaInput.value) : null;
    if (gpaVal !== null && (gpaVal < 0 || gpaVal > 4)) {
        showToast('GPA must be between 0.0 and 4.0.', 'error');
        gpaInput.focus();
        return;
    }

    const payload = {
        name,
        grade:         Number(grade),
        email:         emailInput ? emailInput.value.trim() : '',
        major:         majorInput ? majorInput.value.trim() : '',
        academic_year: yearInput  ? yearInput.value : '',
        gpa:           gpaVal,
        courses:       coursesCtn ? collectCourses(coursesCtn) : [],
        notes:         notesInput ? notesInput.value.trim() : '',
    };

    try {
        const res = await fetch(API.students, {
            method:  'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        if (data.success) {
            showToast(`✅ ${data.student.name} added successfully.`, 'success');
            // Clear form
            nameInput.value = '';
            gradeInput.value = '';
            if (emailInput) emailInput.value = '';
            if (majorInput) majorInput.value = '';
            if (yearInput)  yearInput.value  = '';
            if (gpaInput)   gpaInput.value   = '';
            if (notesInput) notesInput.value = '';
            if (coursesCtn) coursesCtn.innerHTML = '';
            nameInput.focus();
            loadStudents();
        } else {
            showToast(data.error || 'Failed to add student.', 'error');
        }
    } catch (err) {
        showToast('Network error. Could not add student.', 'error');
    }
}

/* ==========================================================================
   DELETE STUDENT
   ========================================================================== */
async function deleteStudent(studentId, name) {
    if (!confirm(`Are you sure you want to remove "${name}"?`)) return;
    try {
        const res = await fetch(`${API.students}/${studentId}`, { method: 'DELETE' });
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        if (data.success) {
            showToast(`🗑️ ${data.student.name} removed.`, 'success');
            loadStudents();
        } else {
            showToast(data.error || 'Failed to delete student.', 'error');
        }
    } catch (err) {
        showToast('Network error. Could not delete student.', 'error');
    }
}

/* ==========================================================================
   EDIT STUDENT MODAL  (full-field update)
   ========================================================================== */
function openEditModal(s) {
    const editModal   = document.getElementById('edit-modal');
    const editIdInput = document.getElementById('edit-student-id');
    const modalName   = document.getElementById('modal-student-name');
    const modalId     = document.getElementById('modal-student-id');

    if (!editModal || !editIdInput || !modalName || !modalId) {
        console.warn('Missing edit-modal elements'); return;
    }

    editIdInput.value = s.student_id;
    modalName.textContent = s.name;
    modalId.textContent   = s.id;

    const setVal = (id, val) => {
        const el = document.getElementById(id);
        if (el) el.value = (val != null && val !== '') ? val : '';
    };

    setVal('edit-student-grade', s.grade);
    setVal('edit-student-gpa',   s.gpa != null ? s.gpa : '');
    setVal('edit-student-email', s.email);
    setVal('edit-student-major', s.major);
    setVal('edit-student-year',  s.academic_year);
    setVal('edit-student-notes', s.notes);

    // Populate courses
    const coursesCtn = document.getElementById('edit-courses-list');
    if (coursesCtn) {
        coursesCtn.innerHTML = '';
        (s.courses || []).forEach(c => addCourseEntry(coursesCtn, c.course, c.grade != null ? c.grade : ''));
    }

    editModal.classList.remove('hidden');
    const gradeEl = document.getElementById('edit-student-grade');
    if (gradeEl) { gradeEl.focus(); gradeEl.select(); }
}

function closeEditModal() {
    const editModal = document.getElementById('edit-modal');
    if (editModal) editModal.classList.add('hidden');
}

async function submitEditStudent(e) {
    e.preventDefault();
    const studentId   = document.getElementById('edit-student-id')?.value;
    const gradeInput  = document.getElementById('edit-student-grade');
    const gpaInput    = document.getElementById('edit-student-gpa');
    const emailInput  = document.getElementById('edit-student-email');
    const majorInput  = document.getElementById('edit-student-major');
    const yearInput   = document.getElementById('edit-student-year');
    const notesInput  = document.getElementById('edit-student-notes');
    const coursesCtn  = document.getElementById('edit-courses-list');

    if (!studentId || !gradeInput) { console.warn('Missing edit form elements'); return; }

    const newGrade = gradeInput.value;
    if (newGrade === '' || isNaN(newGrade) || Number(newGrade) < minGrade || Number(newGrade) > maxGrade) {
        showToast(`Grade must be between ${minGrade} and ${maxGrade}.`, 'error');
        gradeInput.focus();
        return;
    }

    const gpaRaw = gpaInput ? gpaInput.value.trim() : '';
    const gpaVal = gpaRaw !== '' ? parseFloat(gpaRaw) : null;
    if (gpaVal !== null && (gpaVal < 0 || gpaVal > 4)) {
        showToast('GPA must be between 0.0 and 4.0.', 'error');
        gpaInput.focus();
        return;
    }

    const payload = {
        grade:         Number(newGrade),
        gpa:           gpaVal,
        email:         emailInput  ? emailInput.value.trim()  : '',
        major:         majorInput  ? majorInput.value.trim()  : '',
        academic_year: yearInput   ? yearInput.value          : '',
        notes:         notesInput  ? notesInput.value.trim()  : '',
        courses:       coursesCtn  ? collectCourses(coursesCtn) : [],
    };

    try {
        const res = await fetch(`${API.students}/${studentId}`, {
            method:  'PUT',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        if (data.success) {
            showToast(`✏️ ${data.student.name}'s record updated.`, 'success');
            closeEditModal();
            loadStudents();
        } else {
            showToast(data.error || 'Failed to update student.', 'error');
        }
    } catch (err) {
        showToast('Network error. Could not update student.', 'error');
    }
}

/* ==========================================================================
   DETAIL / PROFILE MODAL
   ========================================================================== */
function openDetailModal(s) {
    const modal = document.getElementById('detail-modal');
    const body  = document.getElementById('detail-modal-body');
    if (!modal || !body) { console.warn('Missing detail-modal elements'); return; }

    const gpaDisplay = s.gpa != null ? `<span style="color:${getGpaColor(s.gpa)};font-weight:700;">${s.gpa.toFixed(2)}</span>` : '—';
    const gradeColor = getGradeColor(s.grade);
    const status     = getGradeStatus(s.grade);
    const standingBadge = getStandingBadgeClass(s.standing);

    // Build course pills HTML
    let coursesHtml = '<em style="color:var(--text-dim);font-size:0.85rem;">No courses enrolled.</em>';
    if (s.courses && s.courses.length > 0) {
        const pills = s.courses.map(c => {
            const gradeStr = c.grade != null ? `<span class="cp-grade">${c.grade}</span>` : '';
            return `<span class="course-pill">${escapeHtml(c.course)}${gradeStr}</span>`;
        }).join('');
        coursesHtml = `<div class="course-pill-list">${pills}</div>`;
    }

    body.innerHTML = `
        <div class="profile-grid">
            <div class="profile-field">
                <label>Full Name</label>
                <span>${escapeHtml(s.name)}</span>
            </div>
            <div class="profile-field">
                <label>Student ID</label>
                <span style="font-family:monospace;color:var(--text-muted);">${escapeHtml(s.id)}</span>
            </div>
            <div class="profile-field">
                <label>Email</label>
                <span>${s.email ? escapeHtml(s.email) : '<span style="color:var(--text-dim)">—</span>'}</span>
            </div>
            <div class="profile-field">
                <label>Major / Program</label>
                <span>${s.major ? escapeHtml(s.major) : '<span style="color:var(--text-dim)">—</span>'}</span>
            </div>
            <div class="profile-field">
                <label>Academic Year</label>
                <span>${s.academic_year ? escapeHtml(s.academic_year) : '<span style="color:var(--text-dim)">—</span>'}</span>
            </div>
            <div class="profile-field">
                <label>Overall Grade</label>
                <span style="color:${gradeColor};font-family:'Outfit',sans-serif;font-size:1.2rem;font-weight:700;">${s.grade}
                    &nbsp;<span class="badge ${status.badge}" style="font-size:0.75rem;">${status.label}</span>
                </span>
            </div>
            <div class="profile-field">
                <label>GPA</label>
                <span>${gpaDisplay}</span>
            </div>
            <div class="profile-field">
                <label>Academic Standing</label>
                <span class="badge ${standingBadge}">${s.standing || '—'}</span>
            </div>
        </div>
        <div class="profile-courses">
            <p class="profile-courses-title">Enrolled Courses &amp; Grades</p>
            ${coursesHtml}
        </div>
        ${s.notes ? `
        <div style="margin-top:1.25rem;">
            <p class="profile-courses-title">Academic Notes</p>
            <div class="profile-notes-box">${escapeHtml(s.notes)}</div>
        </div>` : ''}
        <div class="modal-actions" style="margin-top:1rem;">
            <button class="btn btn-secondary" id="detail-open-edit">
                <i class="fa-solid fa-pen-to-square"></i> Edit Record
            </button>
        </div>`;

    document.getElementById('detail-open-edit').addEventListener('click', () => {
        closeDetailModal();
        openEditModal(s);
    });

    modal.classList.remove('hidden');
}

function closeDetailModal() {
    const modal = document.getElementById('detail-modal');
    if (modal) modal.classList.add('hidden');
}

/* ==========================================================================
   SEARCH (live name search with debounce)
   ========================================================================== */
let searchDebounce = null;

async function performSearch(query) {
    try {
        const res = await fetch(`${API.search}?name=${encodeURIComponent(query)}`);
        if (!res.ok) { console.warn(`Search error: ${res.status}`); return; }
        const data = await res.json();

        const container = document.getElementById('search-result-container');
        if (!container) { console.warn('Missing: search-result-container'); return; }

        if (data.found && data.students && data.students.length > 0) {
            const first = data.students[0];
            const resultName  = document.getElementById('result-name');
            const resultId    = document.getElementById('result-id');
            const resultGrade = document.getElementById('result-grade');

            if (resultName)  resultName.textContent  = first.name;
            if (resultId)    resultId.textContent     = first.id;
            if (resultGrade) resultGrade.textContent  =
                data.students.length === 1
                    ? `Grade: ${first.grade}`
                    : `${data.students.length} matches`;

            container.classList.remove('hidden');
            clearHighlight();
            data.students.forEach(s => highlightRow(s.index));
        } else {
            container.classList.add('hidden');
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

/* ==========================================================================
   FILTER (multi-criteria)
   ========================================================================== */
async function applyFilter() {
    const name     = (document.getElementById('search-input')?.value     || '').trim();
    const major    = (document.getElementById('filter-major')?.value      || '').trim();
    const year     = (document.getElementById('filter-year')?.value       || '');
    const standing = (document.getElementById('filter-standing')?.value   || '');
    const minGradeF= (document.getElementById('filter-min-grade')?.value  || '').trim();

    const params = new URLSearchParams();
    if (name)     params.set('name',     name);
    if (major)    params.set('major',    major);
    if (year)     params.set('academic_year', year);
    if (standing) params.set('standing', standing);
    if (minGradeF !== '') params.set('min_grade', minGradeF);

    try {
        const res = await fetch(`${API.filter}?${params.toString()}`);
        if (!res.ok) { showToast(`Filter error (${res.status}).`, 'error'); return; }
        const students = await res.json();
        renderStudentTable(students);
        const activeCount = [...params.values()].filter(v => v !== '').length;
        if (activeCount > 0) {
            showToast(`Filter applied — ${students.length} match(es).`, 'info');
        }
    } catch (err) {
        showToast('Network error during filter.', 'error');
    }
}

function clearFilter() {
    const ids = ['search-input', 'filter-major', 'filter-year', 'filter-standing', 'filter-min-grade'];
    ids.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    const container = document.getElementById('search-result-container');
    if (container) container.classList.add('hidden');
    clearHighlight();
    loadStudents();
    showToast('Filter cleared.', 'info');
}

/* ==========================================================================
   SORT
   ========================================================================== */
async function sortStudents(ascending) {
    try {
        const res = await fetch(`${API.sort}?ascending=${ascending}`);
        if (!res.ok) { showToast(`Sort error (${res.status}).`, 'error'); return; }
        const students = await res.json();
        renderStudentTable(students);
        loadStats();
        showToast(`Sorted ${ascending ? 'Low → High' : 'High → Low'}.`, 'info');
    } catch (err) {
        showToast('Failed to sort.', 'error');
    }
}

/* ==========================================================================
   INITIAL LOAD — wire up all DOM-dependent code after DOM is ready
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {

    // ── Add Student Form ──────────────────────────────────────────────────
    const addForm = document.getElementById('add-student-form');
    if (addForm) addForm.addEventListener('submit', submitAddStudent);

    const btnAddCourse = document.getElementById('btn-add-course');
    if (btnAddCourse) {
        btnAddCourse.addEventListener('click', () => {
            const container = document.getElementById('add-courses-list');
            if (container) addCourseEntry(container);
        });
    }

    // ── Edit Modal ────────────────────────────────────────────────────────
    const editModal     = document.getElementById('edit-modal');
    const modalClose    = document.getElementById('modal-close');
    const btnEditCancel = document.getElementById('btn-edit-cancel');
    const editForm      = document.getElementById('edit-grade-form');

    if (modalClose)    modalClose.addEventListener('click', closeEditModal);
    if (btnEditCancel) btnEditCancel.addEventListener('click', closeEditModal);
    if (editModal)     editModal.addEventListener('click', e => { if (e.target === editModal) closeEditModal(); });
    if (editForm)      editForm.addEventListener('submit', submitEditStudent);

    const btnEditAddCourse = document.getElementById('btn-edit-add-course');
    if (btnEditAddCourse) {
        btnEditAddCourse.addEventListener('click', () => {
            const container = document.getElementById('edit-courses-list');
            if (container) addCourseEntry(container);
        });
    }

    // ── Detail Modal ──────────────────────────────────────────────────────
    const detailModal      = document.getElementById('detail-modal');
    const detailModalClose = document.getElementById('detail-modal-close');
    if (detailModalClose) detailModalClose.addEventListener('click', closeDetailModal);
    if (detailModal)      detailModal.addEventListener('click', e => { if (e.target === detailModal) closeDetailModal(); });

    // ── Escape key closes any open modal ─────────────────────────────────
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape') {
            const em = document.getElementById('edit-modal');
            const dm = document.getElementById('detail-modal');
            if (em && !em.classList.contains('hidden')) closeEditModal();
            if (dm && !dm.classList.contains('hidden')) closeDetailModal();
        }
    });

    // ── Search (live debounced) ───────────────────────────────────────────
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchDebounce);
            const query = searchInput.value.trim();
            const container = document.getElementById('search-result-container');
            if (!query) {
                if (container) container.classList.add('hidden');
                clearHighlight();
                return;
            }
            searchDebounce = setTimeout(() => performSearch(query), 350);
        });
    }

    const btnSearchLocate = document.getElementById('btn-search-locate');
    if (btnSearchLocate) {
        btnSearchLocate.addEventListener('click', () => {
            clearHighlight();
            const name = document.getElementById('result-name')?.textContent;
            if (!name) return;
            document.querySelectorAll('#students-table-body tr').forEach(row => {
                const nc = row.querySelector('.name-cell');
                if (nc && nc.childNodes[0] && nc.childNodes[0].textContent.trim() === name) {
                    row.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    row.classList.add('row-highlight');
                }
            });
        });
    }

    const btnSearchClear = document.getElementById('btn-search-clear');
    if (btnSearchClear) {
        btnSearchClear.addEventListener('click', () => {
            if (searchInput) searchInput.value = '';
            const container = document.getElementById('search-result-container');
            if (container) container.classList.add('hidden');
            clearHighlight();
        });
    }

    // ── Filter buttons ───────────────────────────────────────────────────
    const btnApplyFilter = document.getElementById('btn-apply-filter');
    const btnClearFilter = document.getElementById('btn-clear-filter');
    if (btnApplyFilter) btnApplyFilter.addEventListener('click', applyFilter);
    if (btnClearFilter) btnClearFilter.addEventListener('click', clearFilter);

    // ── Sort buttons ─────────────────────────────────────────────────────
    const btnSortAsc  = document.getElementById('btn-sort-asc');
    const btnSortDesc = document.getElementById('btn-sort-desc');
    if (btnSortAsc)  btnSortAsc.addEventListener('click',  () => sortStudents(true));
    if (btnSortDesc) btnSortDesc.addEventListener('click', () => sortStudents(false));

    // ── Save Database ────────────────────────────────────────────────────
    const btnSaveDb = document.getElementById('btn-save-db');
    if (btnSaveDb) {
        btnSaveDb.addEventListener('click', async () => {
            try {
                const res  = await fetch(API.save, { method: 'POST' });
                if (!res.ok) { showToast(`Save error (${res.status}).`, 'error'); return; }
                const data = await res.json();
                showToast(data.success ? '💾 Database saved.' : 'Save failed.', data.success ? 'success' : 'error');
            } catch (err) {
                showToast('Network error. Could not save.', 'error');
            }
        });
    }

    // ── Initial Data Load ────────────────────────────────────────────────
    loadConfig().then(() => loadStudents());
});

async function loadConfig() {
    try {
        const res = await fetch(API.config);
        if (!res.ok) return;
        const cfg = await res.json();
        if (typeof cfg.min_grade === 'number') minGrade = cfg.min_grade;
        if (typeof cfg.max_grade === 'number') maxGrade = cfg.max_grade;
    } catch (_) {
        // Non-fatal: retain defaults (0 / 100).
    }
}
