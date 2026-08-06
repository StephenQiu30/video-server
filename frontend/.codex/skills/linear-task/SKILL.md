---
name: linear-task
description: Create, rewrite, split, or quality-check Linear issues so each task has an evidence-based problem statement, one executable outcome, explicit scope, falsifiable acceptance criteria, concrete validation, dependencies, and the existing labels required for repository, agent, and reviewer routing. Use when a user asks to create a Linear task, turn a request into an actionable issue, improve a weak issue description, or verify that a proposed issue is ready for execution.
---

# Create a Linear task

Create issues that an implementation agent and reviewer can execute without
guessing. Preserve facts from the request and repository; never manufacture
requirements, evidence, commands, labels, IDs, or dependencies.

## Mutation boundary

- Create an issue only when the user explicitly asks to create or submit it.
- When asked to draft, rewrite, review, or improve an issue, return or apply the
  requested text without creating a second issue.
- Update an existing issue only when the request authorizes that update.
- Ask one focused question before mutation only when a required choice cannot be
  inferred safely and would materially change scope, ownership, routing, or
  acceptance. Otherwise proceed with documented assumptions.

## Workflow

1. Read the request, linked requirements/designs/plans, repository instructions,
   and relevant existing issues. Separate confirmed facts from assumptions.
2. Define one independently deliverable outcome. If the request contains
   multiple outcomes that can ship or fail independently, propose or create
   separate issues and express their relationships.
3. Search the same team/project for open issues with matching component,
   behavior, error text, or outcome. Do not create a duplicate. Report the
   existing issue or, when authorized, improve it instead.
4. Resolve required metadata from project conventions and nearby issues:
   team, project, state, priority when specified, labels, parent/related issues,
   and blocking relationships.
5. Draft the title and body using the contract below. Remove empty optional
   sections and every placeholder before mutation.
6. Run the quality gate. Create or update the issue only when it passes.
7. Re-read the saved issue and verify title, rendered body, state, project,
   labels, and relationships. Repair partial writes when authorized; otherwise
   report the exact mismatch and do not claim completion.
8. Return the issue identifier, title, URL, state, labels, and relationships.

## Metadata rules

- Reuse existing names exactly; never invent near-duplicate labels or states.
- Use the smallest complete label set required for ownership and dispatch.
- When agent routing is enabled, attach one intended `agent:*` label.
- When reviewer routing is enabled, attach one intended `reviewer:*` label.
- Add the established repository/ownership label, such as `repo:*`, plus any
  required `phase:*`, platform, team, or dispatch label.
- Reject conflicting labels in the same class unless the project explicitly
  supports multiple values.
- Prefer `Backlog` for a captured but not execution-ready task. Use `Todo` only
  when the issue is complete, accepted for execution, and project convention or
  the user indicates it should enter the queue. Never move directly to
  `In Progress` merely because the issue was created.
- Represent sequencing with `blockedBy`; use `related` only for non-blocking
  context. Set a parent when the issue is a true child deliverable.

## Title contract

- Name the observable outcome or defect, not the activity of discussing it.
- Keep one subject and one behavior. Use the project language and terminology.
- Avoid vague titles such as "optimize workflow", "handle login issue", or
  "support new requirement". Do not add an issue identifier to the title.

Example:

- Weak: `优化登录问题`
- Strong: `验证码过期时登录接口返回明确的业务错误码`

## Issue body contract

Use the following structure. Keep bullets concise and replace every placeholder
with task-specific content.

```md
## Goal
- <one end state and why it matters>

## Task Description
- Current behavior: <what happens now>
- Evidence: <reproduction, error, metric, code/doc reference, or observed gap>
- Impact: <affected user, system, or delivery consequence>
- Expected behavior: <what must be true instead>

## Scope Boundaries
- In scope: <allowed change>
- Out of scope: <adjacent work explicitly excluded>
- Non-goals: <compatibility, migration, abstraction, or cleanup not required>

## Acceptance Criteria
- AC-01: <observable and falsifiable result>
- AC-02: <boundary, failure-path, or regression result>

## Validation
- Red evidence: <test or executable signal that demonstrates the unmet behavior>
- Automated: <exact relevant test, lint, build, or verification command>
- Manual: <only a user-visible or workflow-visible check that adds signal>
- Agent Review focus: <highest-risk requirement, boundary, and failure mode>

## Deliverables
- <specific code, test, document, configuration, or workflow artifact>
```

Add this section only when relationships exist:

```md
## Relationships
- Parent: <issue>
- Blocked by: <issue and dependency>
- Related: <issue and relevance>
```

## Writing rules

- Describe current code reality separately from target behavior.
- Cite available evidence precisely. If the report is not yet reproduced, say
  `Evidence to capture` and make reproduction the first acceptance/validation
  item; do not present an assumption as observed fact.
- State impact concretely without exaggerating severity or inventing metrics.
- Keep implementation details out of the goal and acceptance criteria unless a
  governing design or explicit requirement mandates them.
- Make each acceptance criterion test one result. Include error handling,
  permissions, state transitions, data boundaries, migration/rollback, or UI
  evidence only when relevant to the task.
- Map every acceptance criterion to at least one validation method. Use exact
  commands only when confirmed from the repository; otherwise name the required
  check without fabricating a command.
- Name deliverables precisely enough to review, but do not guess file paths.
- Use Markdown headings, lists, task lists where useful, and fenced blocks for
  commands or output. Do not submit a prose wall.

## Quality gate

Before creating or updating the issue, confirm:

- The title identifies one concrete outcome.
- The problem statement distinguishes current behavior, evidence, impact, and
  expected behavior.
- The issue is not a duplicate and does not bundle independent deliverables.
- Scope and non-goals prevent foreseeable boundary drift.
- Acceptance criteria are observable, falsifiable, and internally consistent.
- Validation covers every acceptance criterion and does not invent commands.
- Deliverables and applicable dependencies are explicit.
- Team, project, state, priority, labels, and relationships follow existing
  project conventions.
- No placeholder, `TBD`, unsupported claim, empty section, or conflicting label
  remains.

If any required check fails, refine the draft or request the one missing choice
before mutation.

## Completion report

Report only verified saved state:

```text
Created/updated: <identifier> | <title>
URL: <url>
State: <state>
Labels: <labels>
Relationships: <parent / blockedBy / related, or none>
```

If creation or verification partially fails, state what was saved, what is
missing, and whether a duplicate or follow-up mutation must be avoided.
