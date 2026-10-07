# Session 04 — Code & Test Audit + Fix Plan

**Date:** October 2026
**Goal:** Full re-inspection of every source file and test to find remaining
bugs, annotation errors, test gaps, and docs issues. Produce a prioritised fix
plan and create the `ai-prompts/` folder.

**Output Artifact:** [`code-audit-fixes-plan.md`](../code-audit-fixes-plan.md)
**Status:** 🔄 Plan approved — implementation pending

---

## Prompts

### Prompt 1 — Audit request

> recheck code and test for failure and give me structured actions with
> recallable names in your memory, from critical to least critical, dont
> focus too much on specification, try to keep updates to its most optimized
> version, double check for errors and confirm with me the errors by group
> and ill let you know based on what you find what to fix and what to omit

**Bob's response summary:**
Bob read every source file (`models/`, `services/`, `storage/`, `validators/`,
`ui/`, `config.py`, `main.py`, `run_web.py`) and all 6 test files, then
produced a grouped findings report:

**Group A — Logic Bugs (critical)**
- A1: `get_student()` missing `self._lock` — race condition with Flask
- A2: `sort_by_grade()` returns internal list reference — callers can corrupt state
- A3: `get_grade()` hardcodes `0`/`100` instead of using `MIN_GRADE`/`MAX_GRADE`

**Group B — Type annotation mismatches**
- B1: `add_student(grade: int)` and `update_grade(new_grade: int)` — should be `float`
- B2: `_grade_badge(grade: int)` — should be `float`

**Group C — Test gaps**
- C1: `get_student()` has zero direct test coverage
- C2: `is_empty()` has no dedicated test
- C3: `search_all_by_name()` missing from `test_student_manager.py`

**Group D — Minor/style (omitted per user decision)**
- D1: Unused `total_w` variable in `student_table()` — omitted
- D2: Dead `_grade_status()` method — omitted

---

### Prompt 2 — Fix scope decision

> lets do all and omit, D2, D1, add a new folder for the ai prompts i have
> used on you also previous chat, fix github repository saying modified
> version of original creator for the hackathon we are building

**Bob's response summary:**
Bob confirmed the scope:
- Fix A1, A2, A3, B1, B2, C1, C2, C3
- Skip D1 and D2
- Create `ai-prompts/` folder with logs for all 4 sessions
- Update `README.md` with hackathon attribution and original-author credit

---

### Prompt 3 — GitHub handle clarification

> Built by [your GitHub handle] for the IBM Bob Hackathon. Forked and
> extended from [original creator handle]'s student-grade-system.

*(Bob asked for actual handles)*

> My handle is ferreirav and the original creator's handle is the-original-author
> (I'll fill in the real one later — just use placeholders for now)

**Bob's response summary:**
Confirmed: use `ferreirav` as the builder handle; use `the-original-author`
as a placeholder to be replaced with the real handle before submission.

---

### Prompt 4 — Earlier sessions request

> fill in later and earlier conversation text

**Bob's response summary:**
Bob read `robustness-fixes-plan.md`, `polish-robustness-plan.md`, and
`dashboard-stability-plan.md` to reconstruct sessions 01–03 accurately,
then created all 4 session files under `ai-prompts/`.

---

## Findings & Decisions

| ID | Group | Name | Fix |
|----|-------|------|-----|
| A1 | 🔴 Critical | `get_student` missing lock | Wrap body in `with self._lock:` |
| A2 | 🔴 Critical | `sort_by_grade` leaks list ref | Return `list(self._students)` |
| A3 | 🟠 Medium | `get_grade` hardcoded bounds | Import and use `MIN_GRADE`/`MAX_GRADE` |
| B1 | 🟠 Medium | `grade: int` annotation | Change to `float` in both methods |
| B2 | 🟠 Medium | `_grade_badge: int` annotation | Change to `float` |
| C1 | 🟡 Low | `get_student` no test | Add `TestGetStudent` class |
| C2 | 🟡 Low | `is_empty` no test | Add `TestIsEmpty` class |
| C3 | 🟡 Low | `search_all_by_name` not in manager tests | Add `TestSearchAllByName` class |
| D1 | 🔵 Trivial | Unused `total_w` | **Omitted** |
| D2 | 🔵 Trivial | Dead `_grade_status` | **Omitted** |
| NEW | Docs | `ai-prompts/` folder | Created with 4 session logs |
| NEW | Docs | README attribution | Hackathon badge + Credits section |

---

## Output Artifact

Plan file: [`code-audit-fixes-plan.md`](../code-audit-fixes-plan.md)

8 sub-tasks (ST-1 through ST-8), all `[ ] pending`.

---

## Verification

Implementation not yet started — will update this file after each sub-task
is completed and the full test suite re-run.
