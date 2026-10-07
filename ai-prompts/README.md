# AI Prompts — IBM Bob Hackathon Work Log

This folder is the living evidence of IBM Bob usage throughout the
**GradePulse** project, built for the
[Building with IBM Bob Hackathon](https://hackathon.angelhack.com/web/events/building-with-ibm-bob).

---

## Purpose

Every Bob session that produced a plan, a fix, or a decision is
recorded here with:

- The **exact prompts** sent to Bob
- The **goal** of the session
- A **summary of findings or decisions** made
- The **output artifact** (plan file, code change, or document)

This log feeds directly into `submission/bob-work-log.md` and
provides judges with traceable evidence of how IBM Bob was used.

---

## Session Index

| File | Session Goal | Output Artifact | Status |
|------|-------------|-----------------|--------|
| [session-01-app-js-robustness.md](session-01-app-js-robustness.md) | Fix 4 frontend crash/silent-failure bugs in `app.js` | `robustness-fixes-plan.md` | ✅ Done |
| [session-02-polish-robustness.md](session-02-polish-robustness.md) | Fix 5 low-severity polish and test-coverage gaps | `polish-robustness-plan.md` | ✅ Done |
| [session-03-dashboard-stability.md](session-03-dashboard-stability.md) | Fix 17 issues — security, thread safety, frontend hardening, validation | `dashboard-stability-plan.md` | ✅ Done |
| [session-04-code-audit-and-fixes.md](session-04-code-audit-and-fixes.md) | Full code + test audit; produce prioritised fix plan | `code-audit-fixes-plan.md` | 🔄 In Progress |

---

## Format per Session File

Each file follows this structure:

```
# Session N — <title>

**Date:** YYYY-MM-DD
**Goal:** One-sentence summary

## Prompts

### Prompt 1
> exact text sent to Bob

**Bob's response summary:** ...

## Findings / Decisions

## Output Artifact

## Verification
```

---

*Keep this log updated after every Bob session.  Do not claim Bob
authored work done outside these sessions.*
