---
name: git-auto-push
description: Use when the user wants to automatically stage all changes, commit, and push to GitHub — performs a full git add, commit, and push with no confirmation step.
---

# Git Auto-Push

Stage every change, commit with a generated message, and push to the remote. Fully automatic — no confirmation.

## Step 1 — Check git status

Run:
```
git status --short
```
using `execute_command`. If the output is empty (nothing to commit), report "Nothing to commit — working tree clean" and stop.

## Step 2 — Stage all changes

```
git add -A
```

## Step 3 — Generate a commit message

Inspect the staged diff to write a meaningful commit message:
```
git diff --cached --stat
```

Build a single-line commit message using this format:
- If changes span multiple areas: `"chore: update [list of changed areas]"`
- If changes are in one file: `"fix/feat: [what changed] in [filename]"`
- If it is purely README: `"docs: update README"`
- Keep it under 72 characters.

## Step 4 — Commit

```
git commit -m "<generated message>"
```

Use `execute_command` with the exact generated message from Step 3.

## Step 5 — Push

```
git push
```

If the push fails because the remote branch does not exist yet, run:
```
git push --set-upstream origin <current-branch>
```

Get the current branch name with `git branch --show-current` first.

## Step 6 — Confirm

Report:
- The commit hash (from `git log -1 --oneline`)
- The commit message used
- The remote and branch pushed to

If any step fails, show the exact error output and stop — do not retry silently.
