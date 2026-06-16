---
name: harness-linear-loop
description: Use when a Symphony-ready task must keep Linear status, Workpad, pull request links, and validation evidence synchronized through review and merge.
license: MIT
---

# Harness Linear Loop

## Purpose

Close the ticket loop. Local validation is not complete until the plan, PR, status, and evidence are visible from Linear.

## Use When

- A ticket is picked up by `WORKFLOW.md` or a compatible runner.
- The agent needs to update status, checklist, PR link, or evidence.
- UI validation produced screenshot, trace, or video artifacts that should be attached or referenced.

## Standard Contract

Use the configured Linear MCP server or Linear API. If neither is available, write the missing auth/tool blocker into `## Claude Workpad` and stop.

The loop maintains:

- status: `Todo -> In Progress -> Human Review -> Merging -> Done`, with `Rework` for reviewer changes.
- single source of truth: one persistent `## Claude Workpad`.
- links: branch, PR, CI/checks, and artifact references.
- evidence: command output, logs, screenshots, traces, and upload video evidence when supported.
- review gate: no `Human Review` until acceptance criteria, validation, PR feedback, and checks are resolved.

## Flow

0. Open `.claude/skills/harness-quality-gate/SKILL.md` and `.claude/skills/using-superpowers/SKILL.md` before other work.
1. Fetch the ticket and confirm current status before changing files.
2. Move `Todo` to `In Progress` only after the workspace is ready.
3. Create or update `## Claude Workpad` with plan, acceptance criteria, validation checklist, and environment stamp.
4. After implementation, follow `test-driven-development` and `executing-plans`; run `harness-local-server` and `harness-playwright-evidence` when relevant; finish with `verification-before-completion`.
5. Attach or link evidence through Linear API when supported; otherwise paste artifact paths and summaries.
6. Create or update the PR and link it to the ticket.
7. Sweep PR comments and CI before moving to `Human Review`.
8. In `Merging`, follow the repo merge policy, then move the ticket to `Done`.

## Done

- Linear shows current status, checked-off plan, PR link, and validation evidence.
- Humans can inspect the uploaded or linked evidence without asking the agent what happened.
- Rework starts from the latest ticket, Workpad, PR feedback, and `origin/main`.
