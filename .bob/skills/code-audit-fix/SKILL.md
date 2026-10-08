---
name: code-audit-fix
description: Use when the user wants to audit code for bugs, errors, or issues and automatically fix them — scans files, identifies problems, and applies fixes without asking for confirmation.
---

# Code Audit & Auto-Fix

Scan the codebase for bugs and issues, then fix them in place. No confirmation needed — apply every fix directly.

## Step 1 — Identify the scope

1. If the user named specific files or directories, work only those.
2. Otherwise, use `list_files` (recursive) to get the full file tree, then filter to source files only (`.py`, `.js`, `.ts`, `.html`, `.css`, etc.) — skip `__pycache__`, `.git`, `node_modules`, and generated artifacts.

## Step 2 — Audit each file

For each file in scope:

1. Use `read_file` to load its content.
2. Scan for the following categories of issues:
   - **Syntax errors** — invalid syntax that would prevent execution/parsing.
   - **Logic bugs** — off-by-one errors, wrong operators, incorrect conditionals, unreachable code.
   - **Undefined / misused names** — variables used before assignment, typos in identifiers, wrong attribute access.
   - **Missing error handling** — uncaught exceptions where the caller contract requires them.
   - **Dead code** — imports, variables, or functions that are defined but never used.
   - **Type mismatches** — passing the wrong type where a specific type is expected (Python type hints, JS/TS types).
   - **Security issues** — hardcoded secrets, unsanitised inputs, SQL/shell injection risks.
   - **Style violations** — only flag violations that affect correctness or readability significantly; do not reformat for cosmetic reasons.

3. Record every finding as: `FILE:LINE — [CATEGORY] description`.

## Step 3 — Report findings

Before applying any fixes, print a concise list of all findings grouped by file. Format:

```
app/services/student_manager.py
  Line 42 — [LOGIC] off-by-one in slice index
  Line 78 — [DEAD CODE] unused import 'os'

app/validators/input_validator.py
  Line 15 — [TYPE] grade compared to str instead of float
```

If no issues are found in a file, skip it from the report.

## Step 4 — Apply fixes

For each finding, apply the minimal correct fix using `apply_diff` or `search_and_replace`. Rules:
- Fix only what was flagged — do not refactor surrounding code.
- Preserve existing indentation and style.
- If a fix would require understanding business logic you cannot infer from the code, leave a `# TODO: audit-fix — [reason]` comment instead of guessing.

## Step 5 — Summarise

After all fixes are applied, print a short summary:
- Total files scanned
- Total issues found
- Total issues fixed
- Any issues left as TODOs (with file and line)

Use `update_todo_list` to track progress across files if there are more than five files in scope.
