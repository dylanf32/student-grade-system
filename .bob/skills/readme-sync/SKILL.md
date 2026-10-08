---
name: readme-sync
description: Use when the user wants to update or sync the README — regenerates the README to reflect the current project structure, features, and files automatically.
---

# README Sync

Scan the project and rewrite the README to accurately reflect the current state. Preserve existing sections that are still accurate; only update what has drifted.

## Step 1 — Read the current README

Use `read_file` on `README.md` to load the existing content. Identify all top-level sections (headings).

## Step 2 — Scan the project

Gather current facts about the project:

1. **File tree** — use `list_files` (recursive) to build the current directory tree. Skip `.git`, `__pycache__`, `node_modules`, `.pytest_cache`, and any `*.pyc` files.
2. **Entry points** — find the main runnable files (e.g. `main.py`, `run_web.py`, `app.py`). Read a few lines of each to confirm what they do.
3. **Dependencies** — read `requirements.txt` (or `package.json`) if present.
4. **Tests** — list files under `tests/` and extract what each test file covers (read the top-level docstring or first few test function names).
5. **Features** — read `app/` or the main application package to identify active features (menu handlers, routes, etc.).

## Step 3 — Diff README against reality

Compare each README section against what you found in Step 2:

| Section | What to check |
|---|---|
| Project Structure | Does the tree match current files? Any new files or removed files? |
| How to Run | Are the commands still correct? |
| Features | Do listed features match what the code actually implements? |
| Test Coverage | Do the listed test files and descriptions match `tests/`? |
| Any other section | Is the content still accurate? |

List every discrepancy found before making any changes.

## Step 4 — Update the README

Apply targeted edits using `apply_diff` or `search_and_replace`:
- Update only sections that have drifted.
- Do **not** change sections that are still accurate.
- Do **not** alter the writing style or badge layout of sections you are not updating.
- If a new top-level directory or major feature was added that has no README section yet, append a new section at the bottom (before the License section).

## Step 5 — Summarise

Report:
- Which sections were updated and why
- Which sections were left unchanged
- Any new sections added
