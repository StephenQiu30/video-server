---
name: linear-create-task
description: Use when creating a new Linear task or rewriting a Linear task draft so the issue contains a complete execution template with goal, task description, scope boundaries, acceptance criteria, and validation details.
---

# Linear Create Task

Create Linear tasks with execution-ready content. Every new task should be understandable without extra chat context and should be strict enough to support OpenSpec-driven SDD and later Agent Review.

## Rules

- Create or rewrite the issue only when the task scope is concrete enough to execute.
- Keep the issue scoped to one deliverable or one tightly related change set.
- Write the body so it can stand alone as the source of truth for implementation kickoff.
- Require explicit scope boundaries; do not leave room for open-ended compatibility extras or non-essential tests.
- Make validation executable. Prefer commands, checklists, or concrete review evidence over vague statements.

## Required Fields

Use this structure in the Linear issue body:

```md
## Goal
- [clear business or engineering outcome]

## Task Description
- Background:
- Expected change:
- OpenSpec impact:

## Scope Boundaries
- In scope:
- Out of scope:
- Explicit non-goals:

## Acceptance Criteria
- [observable requirement]
- [observable requirement]

## Validation
- Automated:
- Manual:
- Agent Review focus:

## Deliverables
- [code / doc / spec / workflow artifact]
```

## Writing Guidance

### Goal

- State the desired end state, not the implementation plan.
- Prefer one sentence plus one measurable outcome.

### Task Description

- Capture the problem, target behavior, and why the task exists.
- If the task changes long-lived behavior, require the matching OpenSpec change or OpenSpec update path.

### Scope Boundaries

- Tighten boundaries aggressively.
- Call out what must not be added, especially compatibility padding, exploratory extras, and non-essential test expansions.

### Acceptance Criteria

- Write criteria the reviewer can falsify.
- Avoid vague phrases such as "works correctly" or "looks good".

### Validation

- `Automated`: list the exact useful tests or checks that should run.
- `Manual`: only include actions that validate user-visible or workflow-visible outcomes.
- `Agent Review focus`: tell the reviewer what implementation-to-spec gaps, boundary drift, and code quality risks to inspect.

## Task Template

```md
## Goal
- <what outcome must be true after this task lands>

## Task Description
- Background: <current problem or missing capability>
- Expected change: <what should be implemented or updated>
- OpenSpec impact: <new change / continue existing change / baseline-only update>

## Scope Boundaries
- In scope: <what is allowed>
- Out of scope: <what is intentionally excluded>
- Explicit non-goals: <compatibility padding, wording-only checks, unrelated cleanup, etc.>

## Acceptance Criteria
- <criterion 1>
- <criterion 2>
- <criterion 3>

## Validation
- Automated: <exact test, lint, build, or verification commands worth running>
- Manual: <manual checks only if they add signal>
- Agent Review focus: <what must be checked against OpenSpec, code, and boundaries>

## Deliverables
- <files, workflow docs, OpenSpec artifacts, PR evidence, or linked outputs>
```

## Final Check Before Creating The Issue

- Title is specific and implementation-scoped.
- Body includes all required fields.
- Validation is concrete and useful.
- Boundaries are explicit.
- OpenSpec expectation is stated when long-lived behavior changes.
