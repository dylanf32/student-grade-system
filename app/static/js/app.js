/* ==========================================================================
   Student Grade Management System — Frontend Controller
   ========================================================================== */

const API = {
    students:          '/api/students',
    stats:             '/api/stats',
    search:            '/api/search',
    filter:            '/api/filter',
    sort:              '/api/sort',
    save:              '/api/save',
    config:            '/api/config',
    insights:          '/api/insights',
    deadlines:         '/api/deadlines',
    deadlinesUpcoming: '/api/deadlines/upcoming',
};

// Grade bounds — updated from /api/config on load; defaults match config.py.
let minGrade = 0;
let maxGrade = 100;
let passingThreshold = 60;

// Chart.js instances (kept so we can destroy before recreating)
const charts = {};

/* ==========================================================================
   TOAST NOTIFICATION SYSTEM
   ========================================================================== */
function showToast(message, type = 'info') {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const iconMap = { success: 'fa-circle-check', error: 'fa-circle-exclamation', info: 'fa-circle-info' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<i class="fa-solid ${iconMap[type] || iconMap.info}"></i> ${message}`;
    container.appendChild(toast);
    const timerId = setTimeout(() => {
        if (toast.parentNode) toast.parentNode.removeChild(toast);
    }, 5000);
    toast.dataset.timerId = timerId;
}

/* ==========================================================================
   GRADE / STANDING HELPERS
   ========================================================================== */
function getGradeStatus(grade) {
    if (grade >= 90) return { label: 'Excellent',     badge: 'badge-excellent',  icon: '🌟' };
    if (grade >= 80) return { label: 'Good',           badge: 'badge-good',       icon: '👍' };
    if (grade >= 70) return { label: 'Average',        badge: 'badge-average',    icon: '📘' };
    if (grade >= passingThreshold) return { label: 'Passing (D)', badge: 'badge-below-avg', icon: '⚠️' };
    return           { label: 'Failing',               badge: 'badge-failing',    icon: '❌' };
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
    if (s.includes('dean'))  return 'badge-deans-list';
    if (s.includes('good'))  return 'badge-good-standing';
    if (s.includes('satisf')) return 'badge-satisfactory';
    if (s.includes('warning')) return 'badge-warning';
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
   CHART.JS GLOBAL DEFAULTS
   ========================================================================== */
function applyChartDefaults() {
    Chart.defaults.color          = '#a1a1b5';
    Chart.defaults.borderColor    = 'rgba(255,255,255,0.06)';
    Chart.defaults.font.family    = "'Inter', sans-serif";
    Chart.defaults.plugins.legend.labels.color    = '#a1a1b5';
    Chart.defaults.plugins.legend.labels.boxWidth = 12;
    Chart.defaults.plugins.legend.labels.padding  = 18;
}

function destroyChart(key) {
    if (charts[key]) { charts[key].destroy(); delete charts[key]; }
}

/* ==========================================================================
   SIDEBAR NAVIGATION
   ========================================================================== */
function initNav() {
    document.querySelectorAll('.nav-item').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.dataset.tab;
            // Active nav
            document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            // Active tab page
            document.querySelectorAll('.tab-page').forEach(p => p.classList.remove('active'));
            const page = document.getElementById(`tab-${tab}`);
            if (page) page.classList.add('active');
            // Close mobile sidebar
            document.getElementById('sidebar')?.classList.remove('open');
            // Lazy-load analytics when the tab becomes visible
            if (tab === 'analytics') renderAnalyticsCharts();
            if (tab === 'deadlines') loadDeadlines();
        });
    });

    // Mobile hamburger
    const ham  = document.getElementById('btn-hamburger');
    const sidebar = document.getElementById('sidebar');
    if (ham && sidebar) {
        ham.addEventListener('click', () => sidebar.classList.toggle('open'));
    }
}

/* ==========================================================================
   COUNT-UP ANIMATION
   ========================================================================== */
function animateCountUp(el, target, suffix = '', decimals = 0) {
    if (!el) return;
    if (target === null || target === undefined || isNaN(target)) {
        el.textContent = suffix ? target + suffix : (target == null ? '—' : target);
        return;
    }
    const duration = 800;
    const start    = performance.now();
    const from     = 0;

    function step(now) {
        const elapsed  = now - start;
        const progress = Math.min(elapsed / duration, 1);
        const ease     = 1 - Math.pow(1 - progress, 3); // cubic ease-out
        const current  = from + (target - from) * ease;
        el.textContent = current.toFixed(decimals) + suffix;
        if (progress < 1) requestAnimationFrame(step);
    }
    requestAnimationFrame(step);
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
        loadInsights();
    } catch (err) {
        showToast('Failed to load students.', 'error');
    }
}

function renderStudentTable(students) {
    const tbody    = document.getElementById('students-table-body');
    const subtitle = document.getElementById('table-subtitle');
    const emptyState = document.getElementById('students-empty-state');
    if (!tbody) return;

    if (!students || students.length === 0) {
        tbody.innerHTML = '';
        if (subtitle) subtitle.textContent = '0 records';
        if (emptyState) emptyState.classList.remove('hidden');
        document.querySelector('.table-card')?.classList.add('hidden');
        return;
    }

    if (emptyState) emptyState.classList.add('hidden');
    document.querySelector('.table-card')?.classList.remove('hidden');
    if (subtitle) subtitle.textContent = `${students.length} student${students.length !== 1 ? 's' : ''}`;
    tbody.innerHTML = '';

    students.forEach(s => {
        const status      = getGradeStatus(s.grade);
        const gradeColor  = getGradeColor(s.grade);
        const gpaColor    = getGpaColor(s.gpa);
        const gpaDisplay  = s.gpa != null ? s.gpa.toFixed(2) : '—';
        const standingBadge = getStandingBadgeClass(s.standing);
        const gradeBarPct = Math.min(100, Math.max(0, s.grade));

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
            <td>
                <div class="grade-cell-wrap">
                    <span class="grade-num" style="color:${gradeColor};">${s.grade}</span>
                    <div class="grade-bar-bg">
                        <div class="grade-bar-fill" style="width:0%;background:${gradeColor};" data-pct="${gradeBarPct}"></div>
                    </div>
                </div>
            </td>
            <td><span class="gpa-pill" style="color:${gpaColor};">${gpaDisplay}</span></td>
            <td><span class="badge ${standingBadge}">${s.standing || '—'}</span></td>
            <td class="text-right">
                <div class="actions-cell">
                    <button class="btn-action btn-action-view"   title="View Profile"><i class="fa-solid fa-eye"></i></button>
                    <button class="btn-action btn-action-edit"   title="Edit Record"><i class="fa-solid fa-pen-to-square"></i></button>
                    <button class="btn-action btn-action-delete" title="Delete"><i class="fa-solid fa-trash-can"></i></button>
                </div>
            </td>`;

        tr.querySelector('.btn-action-view').addEventListener('click',   () => openDetailModal(s));
        tr.querySelector('.btn-action-edit').addEventListener('click',   () => openEditModal(s));
        tr.querySelector('.btn-action-delete').addEventListener('click', () => openDeleteModal(s.student_id, s.name));

        tbody.appendChild(tr);
    });

    // Animate grade bars into view after a short delay
    requestAnimationFrame(() => {
        tbody.querySelectorAll('.grade-bar-fill').forEach(bar => {
            bar.style.width = bar.dataset.pct + '%';
        });
    });
}

/* ==========================================================================
   FETCH & RENDER: STATISTICS + CHARTS
   ========================================================================== */
async function loadStats() {
    try {
        const res = await fetch(API.stats);
        if (!res.ok) return;
        const stats = await res.json();

        animateCountUp(document.getElementById('stat-total'),    stats.total_students);
        animateCountUp(document.getElementById('stat-average'),  stats.average, '', 1);
        animateCountUp(document.getElementById('stat-highest'),  stats.highest, '', 1);
        animateCountUp(document.getElementById('stat-pass-rate'), stats.passing_rate, '%', 1);
        const gpaEl = document.getElementById('stat-avg-gpa');
        if (stats.avg_gpa != null) {
            animateCountUp(gpaEl, stats.avg_gpa, '', 2);
        } else {
            if (gpaEl) gpaEl.textContent = '—';
        }

        renderDashboardGradeChart(stats.grade_distribution);
        renderDashboardStandingDonut(stats.standing_distribution);

        // Store for analytics tab when it opens
        window._lastStats = stats;

    } catch (_) { /* silently fail */ }
}

/* ==========================================================================
   DASHBOARD CHARTS (Grade bar + Standing donut)
   ========================================================================== */
function renderDashboardGradeChart(distribution) {
    const section = document.getElementById('grade-dist-section');
    const canvas  = document.getElementById('grade-dist-chart');
    if (!section || !canvas) return;

    const bands  = ['A (90-100)', 'B (80-89)', 'C (70-79)', 'D (60-69)', 'F (<60)'];
    const colors = ['#22c55e', '#3b82f6', '#a78bfa', '#f59e0b', '#ef4444'];
    const counts = bands.map(b => (distribution && distribution[b] != null) ? distribution[b] : 0);
    const total  = counts.reduce((a, b) => a + b, 0);

    if (total === 0) { section.style.display = 'none'; return; }
    section.style.display = '';

    destroyChart('dashGrade');
    charts.dashGrade = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: bands,
            datasets: [{
                data:            counts,
                backgroundColor: colors.map(c => c + 'cc'),
                borderColor:     colors,
                borderWidth:     1,
                borderRadius:    6,
            }],
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { callbacks: {
                label: ctx => ` ${ctx.parsed.x} student${ctx.parsed.x !== 1 ? 's' : ''}`,
            }}},
            scales: {
                x: { ticks: { precision: 0 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                y: { grid: { display: false } },
            },
        },
    });
}

function renderDashboardStandingDonut(standingDist) {
    const section = document.getElementById('standing-donut-section');
    const canvas  = document.getElementById('standing-donut-chart');
    if (!section || !canvas || !standingDist) return;

    const labels = Object.keys(standingDist);
    const data   = Object.values(standingDist);
    if (data.reduce((a, b) => a + b, 0) === 0) { section.style.display = 'none'; return; }
    section.style.display = '';

    const STANDING_COLORS = {
        "Dean's List":        '#c4b5fd',
        'Good Standing':      '#34d399',
        'Satisfactory':       '#38bdf8',
        'Academic Warning':   '#fbbf24',
        'Academic Probation': '#f87171',
    };
    const bg = labels.map(l => (STANDING_COLORS[l] || '#a78bfa') + 'cc');
    const border = labels.map(l => STANDING_COLORS[l] || '#a78bfa');

    destroyChart('dashStanding');
    charts.dashStanding = new Chart(canvas, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: bg, borderColor: border, borderWidth: 2, hoverOffset: 8 }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '65%',
            plugins: {
                legend: { position: 'right', labels: { padding: 12, font: { size: 11 } } },
                tooltip: { callbacks: {
                    label: ctx => ` ${ctx.label}: ${ctx.parsed} student${ctx.parsed !== 1 ? 's' : ''}`,
                }},
            },
        },
    });
}

/* ==========================================================================
   ANALYTICS TAB CHARTS
   ========================================================================== */
async function renderAnalyticsCharts() {
    let stats = window._lastStats;
    if (!stats) {
        try {
            const res = await fetch(API.stats);
            if (!res.ok) return;
            stats = await res.json();
            window._lastStats = stats;
        } catch (_) { return; }
    }

    const total = stats.total_students || 0;
    const empty = document.getElementById('analytics-empty');
    const grid  = document.querySelector('.analytics-grid');

    if (total === 0) {
        if (grid)  grid.style.display  = 'none';
        if (empty) empty.classList.remove('hidden');
        return;
    }
    if (grid)  grid.style.display  = '';
    if (empty) empty.classList.add('hidden');

    // Grade distribution bar
    renderAnalyticsGradeBar(stats.grade_distribution);
    // Standing donut
    renderAnalyticsStandingDonut(stats.standing_distribution);
    // Pass/fail donut
    renderAnalyticsPassFailDonut(stats.passing_count, stats.failing_count);
    // Major bar
    renderAnalyticsMajorBar(stats.major_distribution);
}

function renderAnalyticsGradeBar(distribution) {
    const canvas = document.getElementById('analytics-grade-bar');
    if (!canvas) return;
    const bands  = ['A (90-100)', 'B (80-89)', 'C (70-79)', 'D (60-69)', 'F (<60)'];
    const colors = ['#22c55e', '#3b82f6', '#a78bfa', '#f59e0b', '#ef4444'];
    const counts = bands.map(b => (distribution && distribution[b] != null) ? distribution[b] : 0);

    destroyChart('aGrade');
    charts.aGrade = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: ['A', 'B', 'C', 'D', 'F'],
            datasets: [{
                label: 'Students',
                data:            counts,
                backgroundColor: colors.map(c => c + 'bb'),
                borderColor:     colors,
                borderWidth:     2,
                borderRadius:    8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { callbacks: {
                title: (items) => bands[items[0].dataIndex],
                label:  ctx  => ` ${ctx.parsed.y} student${ctx.parsed.y !== 1 ? 's' : ''}`,
            }}},
            scales: {
                y: { ticks: { precision: 0 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false } },
            },
        },
    });
}

function renderAnalyticsStandingDonut(standingDist) {
    const canvas = document.getElementById('analytics-standing-donut');
    if (!canvas || !standingDist) return;

    const labels = Object.keys(standingDist);
    const data   = Object.values(standingDist);
    const COLORS = {
        "Dean's List": '#a78bfa', 'Good Standing': '#10b981',
        'Satisfactory': '#06b6d4', 'Academic Warning': '#f59e0b', 'Academic Probation': '#f43f5e',
    };
    const bg = labels.map(l => (COLORS[l] || '#6366f1') + 'cc');
    const border = labels.map(l => COLORS[l] || '#6366f1');

    destroyChart('aStanding');
    charts.aStanding = new Chart(canvas, {
        type: 'doughnut',
        data: { labels, datasets: [{ data, backgroundColor: bg, borderColor: border, borderWidth: 2, hoverOffset: 8 }] },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 12, font: { size: 11 } } },
                tooltip: { callbacks: {
                    label: ctx => ` ${ctx.label}: ${ctx.parsed} student${ctx.parsed !== 1 ? 's' : ''}`,
                }},
            },
        },
    });
}

function renderAnalyticsPassFailDonut(passing, failing) {
    const canvas = document.getElementById('analytics-passfail-donut');
    if (!canvas) return;

    destroyChart('aPassFail');
    charts.aPassFail = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: ['Passing', 'Failing'],
            datasets: [{
                data:            [passing || 0, failing || 0],
                backgroundColor: ['#10b981bb', '#f43f5ebb'],
                borderColor:     ['#10b981', '#f43f5e'],
                borderWidth:     2,
                hoverOffset:     8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: { position: 'bottom', labels: { padding: 12, font: { size: 11 } } },
                tooltip: { callbacks: {
                    label: ctx => ` ${ctx.label}: ${ctx.parsed} student${ctx.parsed !== 1 ? 's' : ''}`,
                }},
            },
        },
    });
}

function renderAnalyticsMajorBar(majorDist) {
    const canvas = document.getElementById('analytics-major-bar');
    if (!canvas || !majorDist) return;

    const sorted  = Object.entries(majorDist).sort((a, b) => b[1] - a[1]);
    const labels  = sorted.map(e => e[0]);
    const data    = sorted.map(e => e[1]);
    const palette = ['#6366f1', '#3b82f6', '#06b6d4', '#10b981', '#f59e0b', '#f43f5e', '#a78bfa', '#34d399'];

    destroyChart('aMajor');
    charts.aMajor = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [{
                label: 'Students',
                data,
                backgroundColor: labels.map((_, i) => palette[i % palette.length] + 'bb'),
                borderColor:     labels.map((_, i) => palette[i % palette.length]),
                borderWidth:     2,
                borderRadius:    8,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: { legend: { display: false }, tooltip: { callbacks: {
                label: ctx => ` ${ctx.parsed.y} student${ctx.parsed.y !== 1 ? 's' : ''}`,
            }}},
            scales: {
                y: { ticks: { precision: 0 }, grid: { color: 'rgba(255,255,255,0.05)' } },
                x: { grid: { display: false }, ticks: { maxRotation: 35, minRotation: 0 } },
            },
        },
    });
}

/* ==========================================================================
   FETCH & RENDER: SUPPORT PANEL (INSIGHTS)
   ========================================================================== */
async function loadInsights() {
    try {
        const res = await fetch(API.insights);
        if (!res.ok) return;
        const insights = await res.json();

        const panel     = document.getElementById('support-panel');
        const list      = document.getElementById('support-list');
        const badge     = document.getElementById('support-count-badge');
        const threshold = document.getElementById('support-threshold');
        if (!panel || !list) return;

        const flagged = insights.filter(i => i.status === 'needs_attention');

        if (insights.length > 0 && threshold) threshold.textContent = insights[0].threshold;

        if (flagged.length === 0) { panel.style.display = 'none'; return; }

        panel.style.display = '';
        if (badge) badge.textContent = `${flagged.length} student${flagged.length !== 1 ? 's' : ''} flagged`;

        list.innerHTML = '';
        flagged.forEach(item => {
            const row = document.createElement('div');
            row.className = 'support-item';
            row.innerHTML = `
                <div>
                    <span class="support-item-name">${escapeHtml(item.name)}</span>
                    <span style="color:var(--text-muted);font-size:0.8rem;margin-left:0.5rem;">${escapeHtml(item.reason)}</span>
                </div>
                <span class="support-item-grade">${item.grade}</span>`;
            list.appendChild(row);
        });
    } catch (_) { /* non-fatal */ }
}

/* ==========================================================================
   COURSE ENTRY HELPERS
   ========================================================================== */
function addCourseEntry(container, courseName = '', courseGrade = '') {
    const row = document.createElement('div');
    row.className = 'course-entry';
    row.innerHTML = `
        <input type="text"   class="course-name-input"  placeholder="Course name" value="${escapeHtml(courseName)}">
        <input type="number" class="course-grade-input" placeholder="Grade" min="0" max="100" value="${courseGrade !== '' && courseGrade != null ? courseGrade : ''}">
        <button type="button" class="btn-remove-course" title="Remove"><i class="fa-solid fa-xmark"></i></button>`;
    row.querySelector('.btn-remove-course').addEventListener('click', () => row.remove());
    container.appendChild(row);
}

function collectCourses(container) {
    const courses = [];
    for (const entry of container.querySelectorAll('.course-entry')) {
        const name  = entry.querySelector('.course-name-input').value.trim();
        const grade = entry.querySelector('.course-grade-input').value.trim();
        if (!name) continue;
        courses.push({ course: name, grade: grade !== '' ? parseFloat(grade) : null });
    }
    return courses;
}

/* ==========================================================================
   ADD STUDENT DRAWER
   ========================================================================== */
function openAddDrawer() {
    document.getElementById('add-drawer')?.classList.remove('hidden');
    document.getElementById('add-drawer-overlay')?.classList.remove('hidden');
    setTimeout(() => document.getElementById('student-name')?.focus(), 60);
}

function closeAddDrawer() {
    document.getElementById('add-drawer')?.classList.add('hidden');
    document.getElementById('add-drawer-overlay')?.classList.add('hidden');
}

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

    if (!nameInput || !gradeInput) return;

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
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        if (data.success) {
            showToast(`✅ ${data.student.name} added successfully.`, 'success');
            nameInput.value  = '';
            gradeInput.value = '';
            if (emailInput)  emailInput.value  = '';
            if (majorInput)  majorInput.value  = '';
            if (yearInput)   yearInput.value   = '';
            if (gpaInput)    gpaInput.value    = '';
            if (notesInput)  notesInput.value  = '';
            if (coursesCtn)  coursesCtn.innerHTML = '';
            closeAddDrawer();
            loadStudents();
        } else {
            showToast(data.error || 'Failed to add student.', 'error');
        }
    } catch (_) {
        showToast('Network error. Could not add student.', 'error');
    }
}

/* ==========================================================================
   DELETE STUDENT — modal-based confirmation
   ========================================================================== */
let _pendingDeleteId   = null;
let _pendingDeleteName = null;

function openDeleteModal(studentId, name) {
    _pendingDeleteId   = studentId;
    _pendingDeleteName = name;
    const modal = document.getElementById('delete-modal');
    const label = document.getElementById('delete-confirm-name');
    if (label) label.textContent = name;
    modal?.classList.remove('hidden');
}

function closeDeleteModal() {
    _pendingDeleteId   = null;
    _pendingDeleteName = null;
    document.getElementById('delete-modal')?.classList.add('hidden');
}

async function confirmDelete() {
    if (!_pendingDeleteId) return;
    const id   = _pendingDeleteId;
    const name = _pendingDeleteName;
    closeDeleteModal();
    try {
        const res = await fetch(`${API.students}/${id}`, { method: 'DELETE' });
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        if (data.success) {
            showToast(`🗑️ ${data.student.name} removed.`, 'success');
            loadStudents();
        } else {
            showToast(data.error || 'Failed to delete student.', 'error');
        }
    } catch (_) {
        showToast('Network error. Could not delete student.', 'error');
    }
}

/* ==========================================================================
   EDIT STUDENT MODAL
   ========================================================================== */
function openEditModal(s) {
    const editModal   = document.getElementById('edit-modal');
    const editIdInput = document.getElementById('edit-student-id');
    const modalName   = document.getElementById('modal-student-name');
    const modalId     = document.getElementById('modal-student-id');
    if (!editModal || !editIdInput || !modalName || !modalId) return;

    editIdInput.value     = s.student_id;
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
    document.getElementById('edit-modal')?.classList.add('hidden');
}

async function submitEditStudent(e) {
    e.preventDefault();
    const studentId  = document.getElementById('edit-student-id')?.value;
    const gradeInput = document.getElementById('edit-student-grade');
    const gpaInput   = document.getElementById('edit-student-gpa');
    const emailInput = document.getElementById('edit-student-email');
    const majorInput = document.getElementById('edit-student-major');
    const yearInput  = document.getElementById('edit-student-year');
    const notesInput = document.getElementById('edit-student-notes');
    const coursesCtn = document.getElementById('edit-courses-list');

    if (!studentId || !gradeInput) return;

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
    } catch (_) {
        showToast('Network error. Could not update student.', 'error');
    }
}

/* ==========================================================================
   DETAIL / PROFILE MODAL
   ========================================================================== */
function openDetailModal(s) {
    const modal = document.getElementById('detail-modal');
    const body  = document.getElementById('detail-modal-body');
    if (!modal || !body) return;

    const gpaDisplay    = s.gpa != null ? `<span style="color:${getGpaColor(s.gpa)};font-weight:700;">${s.gpa.toFixed(2)}</span>` : '—';
    const gradeColor    = getGradeColor(s.grade);
    const status        = getGradeStatus(s.grade);
    const standingBadge = getStandingBadgeClass(s.standing);

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
            <div class="profile-field"><label>Full Name</label><span>${escapeHtml(s.name)}</span></div>
            <div class="profile-field"><label>Student ID</label><span style="font-family:monospace;color:var(--text-muted);">${escapeHtml(s.id)}</span></div>
            <div class="profile-field"><label>Email</label><span>${s.email ? escapeHtml(s.email) : '<span style="color:var(--text-dim)">—</span>'}</span></div>
            <div class="profile-field"><label>Major / Program</label><span>${s.major ? escapeHtml(s.major) : '<span style="color:var(--text-dim)">—</span>'}</span></div>
            <div class="profile-field"><label>Academic Year</label><span>${s.academic_year ? escapeHtml(s.academic_year) : '<span style="color:var(--text-dim)">—</span>'}</span></div>
            <div class="profile-field">
                <label>Overall Grade</label>
                <span style="color:${gradeColor};font-family:'Outfit',sans-serif;font-size:1.2rem;font-weight:700;">
                    ${s.grade}&nbsp;<span class="badge ${status.badge}" style="font-size:0.7rem;">${status.label}</span>
                </span>
            </div>
            <div class="profile-field"><label>GPA</label><span>${gpaDisplay}</span></div>
            <div class="profile-field"><label>Academic Standing</label><span class="badge ${standingBadge}">${s.standing || '—'}</span></div>
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
    document.getElementById('detail-modal')?.classList.add('hidden');
}

/* ==========================================================================
   SEARCH (live debounced)
   ========================================================================== */
let searchDebounce = null;

async function performSearch(query) {
    try {
        const res = await fetch(`${API.search}?name=${encodeURIComponent(query)}`);
        if (!res.ok) return;
        const data = await res.json();

        const container = document.getElementById('search-result-container');
        if (!container) return;

        if (data.found && data.students && data.students.length > 0) {
            const first = data.students[0];
            const rn = document.getElementById('result-name');
            const ri = document.getElementById('result-id');
            const rg = document.getElementById('result-grade');
            if (rn) rn.textContent = first.name;
            if (ri) ri.textContent = first.id;
            if (rg) rg.textContent = data.students.length === 1
                ? `Grade: ${first.grade}`
                : `${data.students.length} matches`;
            container.classList.remove('hidden');
            clearHighlight();
            data.students.forEach(s => highlightRow(s.index));
        } else {
            container.classList.add('hidden');
            clearHighlight();
        }
    } catch (_) { /* silently fail */ }
}

function highlightRow(index) {
    const row = document.querySelector(`tr[data-index="${index}"]`);
    if (row) { row.classList.add('row-highlight'); row.scrollIntoView({ behavior: 'smooth', block: 'center' }); }
}

function clearHighlight() {
    document.querySelectorAll('.row-highlight').forEach(r => r.classList.remove('row-highlight'));
}

/* ==========================================================================
   FILTER
   ========================================================================== */
async function applyFilter() {
    const name     = (document.getElementById('search-input')?.value     || '').trim();
    const major    = (document.getElementById('filter-major')?.value      || '').trim();
    const year     = (document.getElementById('filter-year')?.value       || '');
    const standing = (document.getElementById('filter-standing')?.value   || '');
    const minGradeF= (document.getElementById('filter-min-grade')?.value  || '').trim();

    const params = new URLSearchParams();
    if (name)      params.set('name',          name);
    if (major)     params.set('major',         major);
    if (year)      params.set('academic_year', year);
    if (standing)  params.set('standing',      standing);
    if (minGradeF) params.set('min_grade',     minGradeF);

    try {
        const res = await fetch(`${API.filter}?${params.toString()}`);
        if (!res.ok) { showToast(`Filter error (${res.status}).`, 'error'); return; }
        const students = await res.json();
        renderStudentTable(students);
        if ([...params.values()].filter(Boolean).length > 0) {
            showToast(`Filter applied — ${students.length} match(es).`, 'info');
        }
    } catch (_) {
        showToast('Network error during filter.', 'error');
    }
}

function clearFilter() {
    ['search-input', 'filter-major', 'filter-year', 'filter-standing', 'filter-min-grade'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.value = '';
    });
    document.getElementById('search-result-container')?.classList.add('hidden');
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
    } catch (_) {
        showToast('Failed to sort.', 'error');
    }
}

/* ==========================================================================
   SAVE DATABASE
   ========================================================================== */
async function saveDatabase() {
    try {
        const res  = await fetch(API.save, { method: 'POST' });
        if (!res.ok) { showToast(`Save error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        showToast(data.success ? '💾 Database saved.' : 'Save failed.', data.success ? 'success' : 'error');
    } catch (_) {
        showToast('Network error. Could not save.', 'error');
    }
}

/* ==========================================================================
   CONFIG LOAD
   ========================================================================== */
async function loadConfig() {
    try {
        const res = await fetch(API.config);
        if (!res.ok) return;
        const cfg = await res.json();
        if (typeof cfg.min_grade        === 'number') minGrade         = cfg.min_grade;
        if (typeof cfg.max_grade        === 'number') maxGrade         = cfg.max_grade;
        if (typeof cfg.passing_threshold === 'number') passingThreshold = cfg.passing_threshold;
    } catch (_) { /* retain defaults */ }
}

/* ==========================================================================
   DOM READY — wire everything up
   ========================================================================== */
document.addEventListener('DOMContentLoaded', () => {
    if (typeof Chart !== 'undefined') applyChartDefaults();

    initNav();

    // ── Add Student drawer ────────────────────────────────────────────────
    document.getElementById('btn-open-add-drawer')?.addEventListener('click', openAddDrawer);
    document.getElementById('btn-close-add-drawer')?.addEventListener('click', closeAddDrawer);
    document.getElementById('add-drawer-overlay')?.addEventListener('click', closeAddDrawer);

    const addForm = document.getElementById('add-student-form');
    if (addForm) addForm.addEventListener('submit', submitAddStudent);

    document.getElementById('btn-add-course')?.addEventListener('click', () => {
        const c = document.getElementById('add-courses-list');
        if (c) addCourseEntry(c);
    });

    // ── Edit modal ────────────────────────────────────────────────────────
    document.getElementById('modal-close')?.addEventListener('click', closeEditModal);
    document.getElementById('btn-edit-cancel')?.addEventListener('click', closeEditModal);
    document.getElementById('edit-modal')?.addEventListener('click', e => { if (e.target.id === 'edit-modal') closeEditModal(); });
    document.getElementById('edit-grade-form')?.addEventListener('submit', submitEditStudent);
    document.getElementById('btn-edit-add-course')?.addEventListener('click', () => {
        const c = document.getElementById('edit-courses-list');
        if (c) addCourseEntry(c);
    });

    // ── Detail modal ──────────────────────────────────────────────────────
    document.getElementById('detail-modal-close')?.addEventListener('click', closeDetailModal);
    document.getElementById('detail-modal')?.addEventListener('click', e => { if (e.target.id === 'detail-modal') closeDetailModal(); });

    // ── Delete confirm modal ──────────────────────────────────────────────
    document.getElementById('delete-modal-close')?.addEventListener('click', closeDeleteModal);
    document.getElementById('delete-cancel-btn')?.addEventListener('click', closeDeleteModal);
    document.getElementById('delete-confirm-btn')?.addEventListener('click', confirmDelete);
    document.getElementById('delete-modal')?.addEventListener('click', e => { if (e.target.id === 'delete-modal') closeDeleteModal(); });

    // ── Escape key ────────────────────────────────────────────────────────
    document.addEventListener('keydown', e => {
        if (e.key !== 'Escape') return;
        if (!document.getElementById('edit-modal')?.classList.contains('hidden'))   closeEditModal();
        if (!document.getElementById('detail-modal')?.classList.contains('hidden')) closeDetailModal();
        if (!document.getElementById('delete-modal')?.classList.contains('hidden')) closeDeleteModal();
        if (!document.getElementById('add-drawer')?.classList.contains('hidden'))   closeAddDrawer();
    });

    // ── Search (live debounced) ───────────────────────────────────────────
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            clearTimeout(searchDebounce);
            const query = searchInput.value.trim();
            if (!query) {
                document.getElementById('search-result-container')?.classList.add('hidden');
                clearHighlight();
                return;
            }
            searchDebounce = setTimeout(() => performSearch(query), 350);
        });
    }

    document.getElementById('btn-search-locate')?.addEventListener('click', () => {
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

    document.getElementById('btn-search-clear')?.addEventListener('click', () => {
        if (searchInput) searchInput.value = '';
        document.getElementById('search-result-container')?.classList.add('hidden');
        clearHighlight();
    });

    // ── Filter / sort ─────────────────────────────────────────────────────
    document.getElementById('btn-apply-filter')?.addEventListener('click', applyFilter);
    document.getElementById('btn-clear-filter')?.addEventListener('click', clearFilter);
    document.getElementById('btn-sort-asc')?.addEventListener('click',  () => sortStudents(true));
    document.getElementById('btn-sort-desc')?.addEventListener('click', () => sortStudents(false));

    // ── Save ──────────────────────────────────────────────────────────────
    document.getElementById('btn-save-db')?.addEventListener('click', saveDatabase);
    document.getElementById('btn-save-db-mobile')?.addEventListener('click', saveDatabase);

    // ── Analytics refresh ─────────────────────────────────────────────────
    document.getElementById('btn-refresh-analytics')?.addEventListener('click', () => {
        window._lastStats = null;
        renderAnalyticsCharts();
    });

    // ── Deadlines tab ─────────────────────────────────────────────────────
    document.getElementById('btn-open-deadline-modal')?.addEventListener('click', () => openDeadlineModal());
    document.getElementById('deadline-modal-close')?.addEventListener('click', closeDeadlineModal);
    document.getElementById('deadline-cancel-btn')?.addEventListener('click', closeDeadlineModal);
    document.getElementById('deadline-modal')?.addEventListener('click', e => { if (e.target.id === 'deadline-modal') closeDeadlineModal(); });
    document.getElementById('deadline-form')?.addEventListener('submit', submitDeadlineForm);

    // Escape key — also close deadline modal
    document.addEventListener('keydown', e => {
        if (e.key === 'Escape' && !document.getElementById('deadline-modal')?.classList.contains('hidden')) {
            closeDeadlineModal();
        }
    }, true);

    // ── Initial load ──────────────────────────────────────────────────────
    loadConfig().then(() => {
        loadStudents();
        loadDeadlineReminders();
    });
});

/* ==========================================================================
   DEADLINE HELPERS
   ========================================================================== */

const URGENCY_CONFIG = {
    overdue:  { label: 'Overdue',    cls: 'deadline-overdue',  icon: 'fa-circle-exclamation' },
    critical: { label: 'Due today/tomorrow', cls: 'deadline-critical', icon: 'fa-fire' },
    high:     { label: 'Due in 3 days', cls: 'deadline-high',  icon: 'fa-triangle-exclamation' },
    medium:   { label: 'Due this week', cls: 'deadline-medium', icon: 'fa-clock' },
    none:     { label: 'Upcoming',   cls: 'deadline-none',     icon: 'fa-calendar' },
};

const TYPE_ICON = {
    assignment: 'fa-file-pen',
    exam:       'fa-graduation-cap',
    project:    'fa-diagram-project',
    other:      'fa-tag',
};

function formatDaysLeft(days) {
    if (days === null || days === undefined) return '—';
    if (days < 0)  return `${Math.abs(days)}d overdue`;
    if (days === 0) return 'Due today';
    if (days === 1) return 'Due tomorrow';
    return `${days}d left`;
}

function formatDate(isoStr) {
    if (!isoStr) return '—';
    const [y, m, d] = isoStr.split('-');
    const months = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    return `${months[parseInt(m, 10) - 1]} ${parseInt(d, 10)}, ${y}`;
}

/* ==========================================================================
   DEADLINE REMINDER PANEL (Dashboard)
   ========================================================================== */
async function loadDeadlineReminders() {
    try {
        const res = await fetch(API.deadlinesUpcoming);
        if (!res.ok) return;
        const items = await res.json();

        const panel = document.getElementById('deadline-reminder-panel');
        const list  = document.getElementById('deadline-reminder-list');
        const badge = document.getElementById('deadline-reminder-badge');
        const navBadge = document.getElementById('deadline-nav-badge');
        if (!panel || !list) return;

        if (items.length === 0) {
            panel.style.display = 'none';
            if (navBadge) { navBadge.textContent = ''; navBadge.classList.add('hidden'); }
            return;
        }

        panel.style.display = '';
        if (badge) badge.textContent = `${items.length} reminder${items.length !== 1 ? 's' : ''}`;
        if (navBadge) {
            navBadge.textContent = items.length;
            navBadge.classList.remove('hidden');
        }

        list.innerHTML = '';
        items.forEach(d => {
            const cfg  = URGENCY_CONFIG[d.urgency] || URGENCY_CONFIG.none;
            const icon = TYPE_ICON[d.type] || TYPE_ICON.other;
            const row  = document.createElement('div');
            row.className = `deadline-reminder-item ${cfg.cls}`;
            row.innerHTML = `
                <div class="dl-reminder-icon"><i class="fa-solid ${icon}"></i></div>
                <div class="dl-reminder-info">
                    <span class="dl-reminder-title">${escapeHtml(d.title)}</span>
                    ${d.course ? `<span class="dl-reminder-course">${escapeHtml(d.course)}</span>` : ''}
                </div>
                <div class="dl-reminder-right">
                    <span class="dl-days-badge ${cfg.cls}">${formatDaysLeft(d.days_left)}</span>
                    <span class="dl-date-str">${formatDate(d.due_date)}</span>
                </div>`;
            list.appendChild(row);
        });

        // Notify once per session for 7/3/1-day thresholds
        const notifyKey = 'dl_notified_' + new Date().toDateString();
        const notified  = JSON.parse(sessionStorage.getItem(notifyKey) || '[]');
        items.forEach(d => {
            if (notified.includes(d.id)) return;
            if (d.urgency === 'overdue') {
                showToast(`🚨 Overdue: "${d.title}" was due ${Math.abs(d.days_left)}d ago.`, 'error');
                notified.push(d.id);
            } else if (d.urgency === 'critical') {
                showToast(`🔥 Due ${d.days_left === 0 ? 'today' : 'tomorrow'}: "${d.title}"`, 'error');
                notified.push(d.id);
            } else if (d.urgency === 'high' && d.days_left <= 3) {
                showToast(`⚠️ Due in ${d.days_left} day${d.days_left !== 1 ? 's' : ''}: "${d.title}"`, 'info');
                notified.push(d.id);
            } else if (d.urgency === 'medium' && d.days_left <= 7) {
                showToast(`📅 Reminder: "${d.title}" due in ${d.days_left} days.`, 'info');
                notified.push(d.id);
            }
        });
        sessionStorage.setItem(notifyKey, JSON.stringify(notified));

    } catch (_) { /* non-fatal */ }
}

/* ==========================================================================
   DEADLINE TABLE (Deadlines tab)
   ========================================================================== */
async function loadDeadlines() {
    try {
        const res = await fetch(API.deadlines);
        if (!res.ok) return;
        const items = await res.json();
        renderDeadlinesTable(items);
    } catch (_) {
        showToast('Failed to load deadlines.', 'error');
    }
}

function renderDeadlinesTable(items) {
    const tbody = document.getElementById('deadlines-table-body');
    const empty = document.getElementById('deadlines-empty-state');
    const card  = document.getElementById('deadlines-table-card');
    if (!tbody) return;

    if (!items || items.length === 0) {
        tbody.innerHTML = '';
        if (empty) empty.classList.remove('hidden');
        if (card)  card.classList.add('hidden');
        return;
    }
    if (empty) empty.classList.add('hidden');
    if (card)  card.classList.remove('hidden');

    tbody.innerHTML = '';
    // Sort: overdue first, then by date asc
    items.sort((a, b) => {
        if (a.due_date < b.due_date) return -1;
        if (a.due_date > b.due_date) return 1;
        return 0;
    });

    items.forEach(d => {
        const cfg   = URGENCY_CONFIG[d.urgency] || URGENCY_CONFIG.none;
        const ticon = TYPE_ICON[d.type] || TYPE_ICON.other;
        const tr    = document.createElement('tr');
        tr.dataset.deadlineId = d.id;

        tr.innerHTML = `
            <td>
                <div style="display:flex;align-items:center;gap:0.5rem;">
                    <i class="fa-solid ${ticon}" style="color:var(--primary);font-size:0.85rem;"></i>
                    <span>${escapeHtml(d.title)}</span>
                </div>
                ${d.description ? `<span class="name-subtext">${escapeHtml(d.description)}</span>` : ''}
            </td>
            <td><span class="badge badge-type-${escapeHtml(d.type)}">${escapeHtml(d.type)}</span></td>
            <td style="color:var(--text-muted);font-size:0.875rem;">${d.course ? escapeHtml(d.course) : '<span style="color:var(--text-dim)">—</span>'}</td>
            <td style="font-size:0.875rem;">${formatDate(d.due_date)}</td>
            <td><span class="deadline-status-badge ${cfg.cls}">${formatDaysLeft(d.days_left)}</span></td>
            <td class="text-right">
                <div class="actions-cell">
                    <button class="btn-action btn-action-edit"   title="Edit"><i class="fa-solid fa-pen-to-square"></i></button>
                    <button class="btn-action btn-action-delete" title="Delete"><i class="fa-solid fa-trash-can"></i></button>
                </div>
            </td>`;

        tr.querySelector('.btn-action-edit').addEventListener('click',   () => openDeadlineModal(d));
        tr.querySelector('.btn-action-delete').addEventListener('click', () => deleteDeadline(d.id, d.title));

        tbody.appendChild(tr);
    });
}

/* ==========================================================================
   DEADLINE MODAL (add / edit)
   ========================================================================== */
function openDeadlineModal(d = null) {
    const modal     = document.getElementById('deadline-modal');
    const titleEl   = document.getElementById('deadline-modal-title');
    const submitBtn = document.getElementById('deadline-submit-btn');
    const editId    = document.getElementById('deadline-edit-id');
    if (!modal) return;

    // Reset form
    document.getElementById('deadline-title').value       = d ? d.title       : '';
    document.getElementById('deadline-type').value        = d ? d.type        : 'assignment';
    document.getElementById('deadline-course').value      = d ? d.course      : '';
    document.getElementById('deadline-due-date').value    = d ? d.due_date    : '';
    document.getElementById('deadline-description').value = d ? d.description : '';
    editId.value = d ? d.id : '';

    if (d) {
        titleEl.innerHTML  = '<i class="fa-solid fa-calendar-pen"></i> Edit Deadline';
        submitBtn.innerHTML = '<i class="fa-solid fa-floppy-disk"></i> Save Changes';
    } else {
        titleEl.innerHTML  = '<i class="fa-solid fa-calendar-plus"></i> Add Deadline';
        submitBtn.innerHTML = '<i class="fa-solid fa-plus"></i> Add Deadline';
    }

    modal.classList.remove('hidden');
    setTimeout(() => document.getElementById('deadline-title')?.focus(), 60);
}

function closeDeadlineModal() {
    document.getElementById('deadline-modal')?.classList.add('hidden');
}

async function submitDeadlineForm(e) {
    e.preventDefault();
    const editId = document.getElementById('deadline-edit-id')?.value;
    const title  = (document.getElementById('deadline-title')?.value || '').trim();
    const dueDate = document.getElementById('deadline-due-date')?.value || '';

    if (!title) { showToast('Title is required.', 'error'); return; }
    if (!dueDate) { showToast('Due date is required.', 'error'); return; }

    const payload = {
        title,
        due_date:    dueDate,
        type:        document.getElementById('deadline-type')?.value || 'assignment',
        course:      (document.getElementById('deadline-course')?.value || '').trim(),
        description: (document.getElementById('deadline-description')?.value || '').trim(),
    };

    const isEdit = !!editId;
    const url    = isEdit ? `${API.deadlines}/${editId}` : API.deadlines;
    const method = isEdit ? 'PUT' : 'POST';

    try {
        const res = await fetch(url, {
            method,
            headers: { 'Content-Type': 'application/json' },
            body:    JSON.stringify(payload),
        });
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        if (data.success) {
            showToast(isEdit ? '✏️ Deadline updated.' : '✅ Deadline added.', 'success');
            closeDeadlineModal();
            loadDeadlines();
            loadDeadlineReminders();
        } else {
            showToast(data.error || 'Failed to save deadline.', 'error');
        }
    } catch (_) {
        showToast('Network error. Could not save deadline.', 'error');
    }
}

async function deleteDeadline(id, title) {
    if (!confirm(`Delete deadline "${title}"?`)) return;
    try {
        const res = await fetch(`${API.deadlines}/${id}`, { method: 'DELETE' });
        if (!res.ok) { showToast(`Server error (${res.status}).`, 'error'); return; }
        const data = await res.json();
        if (data.success) {
            showToast('🗑️ Deadline removed.', 'success');
            loadDeadlines();
            loadDeadlineReminders();
        } else {
            showToast(data.error || 'Failed to delete deadline.', 'error');
        }
    } catch (_) {
        showToast('Network error. Could not delete deadline.', 'error');
    }
}
