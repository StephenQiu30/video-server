---
name: commit
description:
  Create a well-formed git commit from current changes using session history for
  rationale and summary; use when asked to commit, prepare a commit message, or
  finalize staged work.
---

# Commit

## Goals

- Produce a commit that reflects the actual code changes and the session context.
- Follow `WORKFLOW.md` and `CLAUDE.md` commit discipline (allowed types and test-first ordering).
- Include both summary and rationale in the body.

## Allowed commit types

Only these subject prefixes are allowed:

- `test:` — failing tests, fixtures, mocks, acceptance scripts, test-only expectations
- `impl:` — smallest implementation that makes existing red tests pass
- `feat:` — user-visible capability or behavior changes (after prior `test:` unless documented as not scriptable)
- `refactor:` — behavior-preserving cleanup after tests are green
- `docs:` — documentation, examples, workflow text, acceptance notes
- `chore:` — CI, configuration, dependency metadata, generated housekeeping

For feature or behavior work, preserve order: `test:` first, then `impl:`/`feat:`, then optional `refactor:`, `docs:`, or `chore:`.

Do not mix unrelated types in one commit. Split by type when practical.

## Inputs

- Session history for intent and rationale.
- `git status`, `git diff`, and `git diff --staged` for actual changes.
- `WORKFLOW.md`, `CLAUDE.md`, and workpad `Commit Plan` when present.

## Steps

1. Read session history to identify scope, intent, and rationale.
2. Inspect the working tree and staged changes (`git status`, `git diff`, `git diff --staged`).
3. Stage intended changes (`git add -A`) after confirming scope.
4. Sanity-check newly added files; flag build artifacts, logs, or temp files before committing.
5. If staging is incomplete or includes unrelated files, fix the index or ask for confirmation.
6. Choose the allowed type that matches the staged diff. Do not use `fix:` or scoped conventional types unless documented as an exception.
7. Write a subject line in imperative mood, <= 72 characters. Format: `<type> <short summary>`.
8. Write a body with summary, rationale, and tests or validation run (or why not run).
9. Wrap body lines at 72 characters.
10. Create the commit message with a here-doc or temp file and use `git commit -F <file>`.
11. Commit only when the message matches the staged changes.

## Output

- A single commit whose message reflects the session and discipline above.

## Template

```
<type> <short summary>

Summary:
- <what changed>

Rationale:
- <why>

Tests:
- <command or "not run (reason)">
```
