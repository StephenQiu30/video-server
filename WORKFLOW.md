---
tracker:
  kind: linear
  project_slug: "$SYMPHONY_LINEAR_PROJECT_SLUG"
  active_states:
    - Todo
    - In Progress
    - Agent Review
    - Merging
    - Rework
  terminal_states:
    - Closed
    - Cancelled
    - Canceled
    - Duplicate
    - Blocked
    - Done
polling:
  interval_ms: 5000
server:
  host: "0.0.0.0"
workspace:
  root: "$SYMPHONY_WORKSPACE_ROOT"
hooks:
  after_create: |
    target_branch="${SYMPHONY_TARGET_BRANCH:-main}"
    git clone --depth 1 --branch "$target_branch" "$SOURCE_REPO_URL" .
    if [ -f package.json ] && command -v npm >/dev/null 2>&1; then
      npm install
    fi
    if [ -f apps/api/requirements.txt ] && command -v python3 >/dev/null 2>&1; then
      python3 -m pip install -r apps/api/requirements.txt
    fi
  before_remove: |
    git status --short || true
agent:
  default_runtime: claude
  max_concurrent_agents: 4
  max_turns: 20
  runtime_by_label:
    agent:codex: codex
    agent:claude: claude
    agent:cursor: cursor
    agent:gemini: gemini
codex:
  command: codex --config shell_environment_policy.inherit=all --config 'model="gpt-5.5"' --config model_reasoning_effort=xhigh app-server
  approval_policy: never
  thread_sandbox: danger-full-access
  turn_sandbox_policy:
    type: dangerFullAccess
claude:
  command: claude -p --dangerously-skip-permissions --permission-mode bypassPermissions
  prompt_mode: stdin
cursor:
  command: cursor-agent -p --force --sandbox disabled --output-format stream-json --stream-partial-output --approve-mcps
  prompt_mode: argument
gemini:
  command: gemini
---

You are working on a Linear ticket `{{ issue.identifier }}`

{% if attempt %}
Continuation context:

- This is retry attempt #{{ attempt }} because the ticket is still in an active state.
- Resume from the current workspace state instead of restarting from scratch.
- Do not repeat already-completed investigation or validation unless needed for new code changes.
- Do not end the turn while the issue remains in an active state unless a true external blocker has been recorded and the issue has been moved to `Blocked`.
  {% endif %}

Issue context:
Identifier: {{ issue.identifier }}
Title: {{ issue.title }}
Current status: {{ issue.state }}
Labels: {{ issue.labels }}
URL: {{ issue.url }}

Description:
{% if issue.description %}
{{ issue.description }}
{% else %}
No description provided.
{% endif %}

Instructions:

1. This is an unattended orchestration session. Never ask a human to perform follow-up actions.
2. Only stop early for a true external blocker (missing required non-GitHub auth, permissions, secrets, or services). If blocked, record it in the workpad and move the issue to `Blocked`.
3. Final message must report completed actions and blockers only. Do not include "next steps for user".

Work only in the provided repository copy. Do not touch any other path.

This video-server workflow runs Claude by default. Use the `claude:` configuration
key, `.claude/` paths, and the `## Claude Workpad` marker throughout this
workflow. Override runtime with `agent:codex`, `agent:cursor`, or `agent:gemini`
labels when Symphony routes a ticket to another agent.

## Prerequisite: Linear access is available

The agent should be able to talk to Linear, either via a configured Linear MCP server, an injected `linear_graphql` tool, or the `LINEAR_API_KEY` environment variable with direct GraphQL HTTP requests to `https://api.linear.app/graphql`. If none are present, record the missing Linear access in the workpad and move the issue to `Blocked`.

## Default posture

- Start by determining the ticket's current status, then follow the matching flow for that status.
- Start every task by opening the tracking workpad comment and bringing it up to date before doing new implementation work.
- Start every task by locating or creating the relevant OpenSpec change artifacts and use them as the SDD source of truth during execution.
- Spend extra effort up front on planning and verification design before implementation.
- Reproduce first: always confirm the current behavior/issue signal before changing code so the fix target is explicit.
- Follow TDD/test-first by default: define the expected behavior as a failing automated test or executable validation before implementation. If a test cannot be written first, document the reason in the workpad and add the closest executable acceptance check before coding.
- Keep ticket metadata current (state, checklist, acceptance criteria, links).
- Treat a single persistent Linear comment as the source of truth for progress.
- Use that single workpad comment for all progress and handoff notes; do not post separate "done"/summary comments.
- Treat any ticket-authored `Validation`, `Test Plan`, or `Testing` section as non-negotiable acceptance input: mirror it in the workpad and execute it before considering the work complete.
- When meaningful out-of-scope improvements are discovered during execution,
  file a separate Linear issue instead of expanding scope. The follow-up issue
  must include a clear title, description, and acceptance criteria, be placed in
  `Backlog`, be assigned to the same project as the current issue, link the
  current issue as `related`, and use `blockedBy` when the follow-up depends on
  the current issue.
- Move status only when the matching quality bar is met.
- Operate autonomously end-to-end unless blocked by missing non-GitHub requirements, secrets, permissions, or services.
- Cover sandbox permissions through workflow command/sandbox configuration and allowed workspace paths; do not mark an issue blocked only because a command needs broader sandbox access.
- Git and GitHub permission problems are not blockers by default; exhaust remote, auth, branch, fork, PR, and manual-link fallbacks before using the blocked-access escape hatch.
- Use the blocked-access escape hatch only for true external blockers after exhausting documented fallbacks.

## Harness + Superpowers (required for execution quality)

Follow `.claude/skills/harness-quality-gate/SKILL.md` as the master checklist. It wires Harness skills with [obra/superpowers](https://github.com/obra/superpowers) for planning, TDD, execution, E2E evidence, and pre-review verification.

Mandatory Superpowers skills by phase:

- Session / planning: `using-superpowers`, `writing-plans`
- OpenSpec / SDD: `openspec-new-change`, `openspec-apply-change`, `openspec-verify-change`, and when continuing existing work `openspec-continue-change`
- Red → green: `test-driven-development` (must align with `test:` then `impl:`/`feat:` commits)
- Implementation: `executing-plans`; use `systematic-debugging` when blocked on failures
- Runtime / E2E: `agent-browser`, `harness-local-server`, `harness-playwright-evidence` when UI or app-touching
- Handoff: `verification-before-completion`, `requesting-code-review`

## Related skills

- `harness-quality-gate`: master Harness + Superpowers checklist for this workflow.
- `linear`: interact with Linear.
- `commit`: produce clean, logical commits during implementation; follow `## Commit discipline` and `.claude/skills/commit/SKILL.md`.
- `push`: keep remote branch current and publish updates.
- `pull`: keep branch updated with latest `origin/main` before handoff.
- `land`: when ticket reaches `Merging`, explicitly open and follow `.claude/skills/land/SKILL.md`, which includes the `land` loop.

## Commit discipline

Allowed commit types are fixed: `test:`, `docs:`, `impl:`, `chore:`, `feat:`, and `refactor:`.

- New work branches must use ASCII slug names with an intent prefix, such as
  `feature/ste-123-short-topic`, `fix/ste-123-short-topic`,
  `chore/ste-123-short-topic`, `docs/ste-123-short-topic`, or
  `refactor/ste-123-short-topic`; never create branches containing Chinese or
  other non-ASCII characters.
- Derive branch slugs from the issue identifier plus a short English topic; keep
  Chinese issue titles for PR titles, commit messages, and workpad notes only.
- Use `test:` for failing tests, fixtures, mocks, acceptance scripts, and test-only expectations.
- Use `impl:` for the smallest implementation that makes existing red tests pass.
- Use `feat:` for user-visible capability or behavior changes, backed by prior `test:` evidence unless explicitly documented as not scriptable.
- Use `refactor:` only after tests are green, and do not change verified behavior.
- Use `docs:` for documentation, examples, workflow text, and acceptance notes.
- Use `chore:` for CI, configuration, dependency metadata, generated housekeeping, or repository maintenance.
- For feature and behavior work, preserve test-first commit order: `test:` first, then `impl:`/`feat:`, then optional `refactor:`, `docs:`, or `chore:` cleanup.
- Do not mix unrelated commit types in one commit. If a change spans tests, implementation, and docs, split commits by type whenever practical.


## Status map

- `Backlog` -> out of scope for this workflow; do not modify.
- `Todo` -> queued; immediately transition to `In Progress` before active work.
  - Special case: if a PR is already attached, treat as feedback/rework loop (run full PR feedback sweep, address or explicitly push back, revalidate, return to `Agent Review`).
- `In Progress` -> implementation actively underway.
- `Agent Review` -> PR is ready for an agent to review. If issues are found, move to Rework, otherwise move to Human Review.
- `Human Review` -> PR is attached and validated; waiting on human approval.
- `Merging` -> approved by human; execute the `land` skill flow (do not call `gh pr merge` directly).
- `Rework` -> reviewer requested changes; planning + implementation required.
- `Blocked` -> waiting on a true external dependency; do not modify until a human unblocks or moves it back to `Todo`/`Rework`.
- `Done` -> terminal state; no further action required.

## Step 0: Determine current ticket state and route

1. Fetch the issue by explicit ticket ID.
2. Read the current state.
3. Route to the matching flow:
   - `Backlog` -> do not modify issue content/state; stop and wait for human to move it to `Todo`.
   - `Todo` -> immediately move to `In Progress`, then ensure bootstrap workpad comment exists (create if missing), then start execution flow.
     - If PR is already attached, start by reviewing all open PR comments and deciding required changes vs explicit pushback responses.
   - `In Progress` -> continue execution flow from current scratchpad comment and current OpenSpec change artifacts.
   - `Agent Review` -> run the `code-review` skill. Review the PR, workpad checklist, and the linked OpenSpec proposal/specs/design/tasks against the implementation. If issues are found, leave comments, restore the developer's `agent:*` label, and move to `Rework`. If approved, move to `Human Review`.
   - `Human Review` -> wait and poll for decision/review updates.
   - `Merging` -> on entry, open and follow `.claude/skills/land/SKILL.md`; do not call `gh pr merge` directly.
   - `Rework` -> run rework flow.
   - `Blocked` -> stop; leave the workpad blocker brief intact and wait for a human to unblock or move it back to an active state.
   - `Done` -> do nothing and shut down.
4. Check whether a PR already exists for the current branch and whether it is closed.
   - If a branch PR exists and is `CLOSED` or `MERGED`, treat prior branch work as non-reusable for this run.
   - Create a fresh branch from `origin/main` and restart execution flow as a new attempt.
5. For `Todo` tickets, do startup sequencing in this exact order:
   - `update_issue(..., state: "In Progress")`
   - find/create `## Claude Workpad` bootstrap comment
   - only then begin analysis/planning/implementation work.
6. Add a short comment if state and issue content are inconsistent, then proceed with the safest flow.

## Step 1: Start/continue execution (Todo or In Progress)

1.  Find or create a single persistent scratchpad comment for the issue:
    - Search existing comments for a marker header: `## Claude Workpad`.
    - Ignore resolved comments while searching; only active/unresolved comments are eligible to be reused as the live workpad.
    - If found, reuse that comment; do not create a new workpad comment.
    - If not found, create one workpad comment and use it for all updates.
    - Persist the workpad comment ID and only write progress updates to that ID.
2.  If arriving from `Todo`, do not delay on additional status transitions: the issue should already be `In Progress` before this step begins.
3.  Immediately reconcile the workpad before new edits:
    - Check off items that are already done.
    - Expand/fix the plan so it is comprehensive for current scope.
    - Ensure `Acceptance Criteria` and `Validation` are current and still make sense for the task.
4.  Start work by writing/updating a hierarchical plan in the workpad comment.
5.  Ensure the workpad includes a compact environment stamp at the top as a code fence line:
    - Format: `<host>:<abs-workdir>@<short-sha>`
    - Example: `devbox-01:/home/dev-user/code/symphony-workspaces/MT-32@7bdde33bc`
    - Do not include metadata already inferable from Linear issue fields (`issue ID`, `status`, `branch`, `PR link`).
6.  Add explicit acceptance criteria and TODOs in checklist form in the same comment.
    - If changes are user-facing, include a UI walkthrough acceptance criterion that describes the end-to-end user path to validate.
    - If changes touch app files or app behavior, add explicit app-specific flow checks to `Acceptance Criteria` in the workpad (for example: launch path, changed interaction path, and expected result path).
    - If the ticket description/comment context includes `Validation`, `Test Plan`, or `Testing` sections, copy those requirements into the workpad `Acceptance Criteria` and `Validation` sections as required checkboxes (no optional downgrade).
7.  Add a `Test-first Evidence` section to the workpad that names the failing test, acceptance script, or executable validation that will prove the change.
8.  Open and follow `.claude/skills/openspec-new-change/SKILL.md` or `.claude/skills/openspec-continue-change/SKILL.md` first, then `.claude/skills/writing-plans/SKILL.md` and `.claude/skills/using-superpowers/SKILL.md`; refine the workpad plan from their output and link the OpenSpec artifacts in the workpad.
9.  Run a principal-style self-review of the plan and refine it in the comment.
10. Before implementing, capture a concrete reproduction signal and record it in the workpad `Notes` section (command/output, screenshot, or deterministic UI behavior).
11. Open and follow `.claude/skills/test-driven-development/SKILL.md`: run the selected test/validation and record the expected red/failing result. If the task is docs-only or cannot have a red test, record the explicit reason and the executable validation that will replace it.
12. Run the `pull` skill to sync with latest `origin/main` before any code edits, then record the pull/sync result in the workpad `Notes`.
    - Include a `pull skill evidence` note with:
      - merge source(s),
      - result (`clean` or `conflicts resolved`),
      - resulting `HEAD` short SHA.
13. Compact context and proceed to execution.

## PR submission content (Test-First required)

Every PR body must follow the repository pull request template and make the test-first story reviewable before `Human Review`.

PR descriptions must be written as valid Markdown: use heading levels for each required section, bullets or numbered lists for grouped details, fenced code blocks for commands/output, and GitHub task-list checkboxes for reviewer checklist items. Do not submit plain-text blobs, malformed headings, or ad-hoc formatting that does not render cleanly on GitHub.

Required PR sections:

- `PR Summary`: concise scope, behavior changed, and impact.
- `Test-first Evidence`: failing `test:` commit or documented exception, whether the test failed before implementation, and the matching green commit/result.
- `Tests added`: mark the relevant test types, or explicitly mark why no new test is applicable.
- `Commands run`: exact commands used for red and green validation.
- `Result`: before/after outcome, including failures before implementation and passing result after implementation.
- `Agent Usage`: separate human-authored acceptance criteria, test cases, and edge cases from agent-generated implementation, refactor, and boilerplate.
- `Reviewer Checklist`: keep all checklist items present so reviewers can audit tests first, minimal implementation, unrelated changes, agent code, and CI.

If a PR cannot satisfy the test-first sections because the change is docs-only, CI-only, generated metadata, or another non-scriptable case, the PR body must explicitly state the exception, the substitute validation, and any follow-up test obligation.


## PR feedback sweep protocol (required)

When a ticket has an attached PR, run this protocol before moving to `Human Review`:

1. Identify the PR number from issue links/attachments.
2. Gather feedback from all channels:
   - Top-level PR comments (`gh pr view --comments`).
   - Inline review comments (`gh api repos/<owner>/<repo>/pulls/<pr>/comments`).
   - Review summaries/states (`gh pr view --json reviews`).
3. Treat every actionable reviewer comment (human or bot), including inline review comments, as blocking until one of these is true:
   - code/test/docs updated to address it, or
   - explicit, justified pushback reply is posted on that thread.
4. Update the workpad plan/checklist to include each feedback item and its resolution status.
5. Re-run validation after feedback-driven changes and push updates.
6. Repeat this sweep until there are no outstanding actionable comments.

## Blocked-access escape hatch (required behavior)

Use this only when completion is blocked by missing required tools, non-GitHub auth/permissions, secrets, or external services that cannot be resolved in-session.

- GitHub and git access are **not** valid blockers by default. Always try fallback strategies first (alternate remote/auth mode, branch or fork push, PR update fallback, manual PR link in the workpad), then continue publish/review flow.
- Do not move to `Blocked` for GitHub access/auth until all fallback strategies have been attempted and documented in the workpad.
- If a non-GitHub required tool is missing, or required non-GitHub auth is unavailable, move the ticket to `Blocked` with a short blocker brief in the workpad that includes:
  - what is missing,
  - why it blocks required acceptance/validation,
  - exact human action needed to unblock.
- Keep the brief concise and action-oriented; do not add extra top-level comments outside the workpad.

## Step 2: Execution phase (Todo -> In Progress -> Agent Review)

1.  Determine current repo state (`branch`, `git status`, `HEAD`) and verify the kickoff `pull` sync result is already recorded in the workpad before implementation continues.
2.  If current issue state is `Todo`, move it to `In Progress`; otherwise leave the current state unchanged.
3.  Load the existing workpad comment and treat it as the active execution checklist.
    - Edit it liberally whenever reality changes (scope, risks, validation approach, discovered tasks).
4.  Do not implement until the workpad contains `Test-first Evidence` with a red/failing test result, or a documented exception plus substitute executable validation.
5.  Open and follow `.claude/skills/executing-plans/SKILL.md` while implementing; use `.claude/skills/systematic-debugging/SKILL.md` when investigation stalls.
6.  Implement against the hierarchical TODOs and keep the comment current:
    - Check off completed items.
    - Add newly discovered items in the appropriate section.
    - Keep parent/child structure intact as scope evolves.
    - Update the workpad immediately after each meaningful milestone (for example: reproduction complete, code change landed, validation run, review feedback addressed).
    - Never leave completed work unchecked in the plan.
    - For tickets that started as `Todo` with an attached PR, run the full PR feedback sweep protocol immediately after kickoff and before new feature work.
7.  Run validation/tests required for the scope.
    - Mandatory gate: execute all ticket-provided `Validation`/`Test Plan`/ `Testing` requirements when present; treat unmet items as incomplete work.
    - Prefer a targeted proof that directly demonstrates the behavior you changed.
    - You may make temporary local proof edits to validate assumptions (for example: tweak a local build input for `make`, or hardcode a UI account / response path) when this increases confidence.
    - Revert every temporary proof edit before commit/push.
    - Document these temporary proof steps and outcomes in the workpad `Validation`/`Notes` sections so reviewers can follow the evidence.
    - If app-touching, run `agent-browser` plus `harness-local-server` and `harness-playwright-evidence` (or `launch-app` / `github-pr-media` when configured) before handoff.
8.  Open and follow `.claude/skills/verification-before-completion/SKILL.md`; paste proof commands/output into Workpad `Validation` / `Notes`.
9.  Re-check all acceptance criteria and close any gaps.
10. Before every `git push` attempt, run the required validation for your scope and confirm it passes; if it fails, address issues and rerun until green, then commit and push changes using only the allowed commit types (`test:`, `docs:`, `impl:`, `chore:`, `feat:`, `refactor:`).
11. Attach PR URL to the issue (prefer attachment; use the workpad comment only if attachment is unavailable).
    - Ensure the GitHub PR has label `symphony` (add it if missing).
    - Ensure the PR body follows `PR submission content (Test-First required)` and includes the full test-first evidence before requesting review.
12. Merge latest `origin/main` into branch, resolve conflicts, and rerun checks.
13. Update the workpad comment with final checklist status and validation notes.
    - Mark completed plan/acceptance/validation checklist items as checked.
    - Add final handoff notes (commit + validation summary) in the same workpad comment.
    - Do not include PR URL in the workpad comment; keep PR linkage on the issue via attachment/link fields.
    - Add a short `### Confusions` section at the bottom when any part of task execution was unclear/confusing, with concise bullets.
    - Do not post any additional completion summary comment.
14. Open and follow `.claude/skills/requesting-code-review/SKILL.md`, then before moving to `Human Review`, poll PR feedback and checks:
    - Run `.claude/skills/openspec-verify-change/SKILL.md` and compare implementation, validation evidence, and PR/workpad notes against the current OpenSpec artifacts.
    - Read the PR `Manual QA Plan` comment (when present) and use it to sharpen UI/runtime test coverage for the current change.
    - Run the full PR feedback sweep protocol.
    - Confirm PR checks are passing (green) after the latest changes.
    - Confirm the PR body is valid Markdown and includes Test-first Evidence, Tests added, Commands run, Result, Agent Usage, and Reviewer Checklist sections with current data.
    - Confirm every required ticket-provided validation/test-plan item is explicitly marked complete in the workpad.
    - Repeat this check-address-verify loop until no outstanding comments remain and checks are fully passing.
    - Re-open and refresh the workpad before state transition so `Plan`, `Acceptance Criteria`, and `Validation` exactly match completed work.
15. Only then prepare to move the issue to `Agent Review`.
    - Check if the issue has a `reviewer:*` label (e.g. `reviewer:claude`, `reviewer:codex`).
    - If a specific reviewer label is present, update the `agent:*` label on the ticket to match the requested reviewer before changing the state.
    - Finally, move the issue to `Agent Review`.
    - Exception: if blocked by missing required non-GitHub tools/auth per the blocked-access escape hatch, move to `Blocked` with the blocker brief and explicit unblock actions.
16. For `Todo` tickets that already had a PR attached at kickoff:
    - Ensure all existing PR feedback was reviewed and resolved, including inline review comments (code changes or explicit, justified pushback response).
    - Ensure branch was pushed with any required updates.
    - Then move to `Agent Review` (applying the same label checking logic as step 15).

## Step 3: Agent Review, Human Review and merge handling

1. When the issue is in `Agent Review`, the designated reviewing agent should execute the `code-review` skill and compare the delivered change against the linked OpenSpec proposal/specs/design/tasks and `openspec/specs/` baseline.
   - Use `requesting-code-review` and superpowers TDD tools for code review if needed.
   - Update the workpad `### Agent Review` section with review status, reviewer identity, findings, required fixes, and verification expectations.
   - If the code has issues, record each issue as an unchecked finding in `### Agent Review`, move the issue to `Rework`, and restore the original `agent:*` label so the implementation agent can fix them. Do not move to `Human Review` from a failed agent review.
   - If the code passes review, mark the review status as approved in `### Agent Review` and move the issue to `Human Review`.
2. When the issue is in `Human Review`, do not code or change ticket content.
3. Poll for updates as needed, including GitHub PR review comments from humans and bots.
4. If review feedback requires changes, move the issue to `Rework` and follow the rework flow.
5. If approved, human moves the issue to `Merging`.
5. When the issue is in `Merging`, open and follow `.claude/skills/land/SKILL.md`, then run the `land` skill in a loop until the PR is merged. Do not call `gh pr merge` directly.
6. After merge is complete, move the issue to `Done`.

## Step 4: Rework handling

1. Treat `Rework` as a full approach reset, not incremental patching.
2. Re-read the full issue body and all human comments; explicitly identify what will be done differently this attempt.
   - Read the workpad `### Agent Review` section first and convert every unchecked finding into the new plan/validation checklist.
3. Close the existing PR tied to the issue.
4. Remove the existing `## Claude Workpad` comment from the issue.
5. Create a fresh branch from `origin/main`.
6. Start over from the normal kickoff flow:
   - If current issue state is `Todo`, move it to `In Progress`; otherwise keep the current state.
   - Create a new bootstrap `## Claude Workpad` comment.
   - Build a fresh plan/checklist and execute end-to-end.
   - Re-run every required Step 1/2 gate, including PR feedback sweep, checks, validation, PR metadata, and the full `Completion bar before Agent Review`.
   - After rework fixes are complete, move only to `Agent Review`; the reviewer is the only agent that may approve the issue into `Human Review`.
   - Preserve the issue's `reviewer:*` label if present, or add `reviewer:claude` before returning to `Agent Review`.

## Completion bar before Agent Review

- Step 1/2 checklist is fully complete and accurately reflected in the single workpad comment.
- Acceptance criteria and required ticket-provided validation items are complete.
- Test-first evidence is recorded: red/failing test or documented exception before implementation, followed by green validation for the latest commit.
- Commit history uses only allowed types (`test:`, `docs:`, `impl:`, `chore:`, `feat:`, `refactor:`) and preserves test-first ordering for feature or behavior work.
- Validation/tests are green for the latest commit.
- PR feedback sweep is complete and no actionable comments remain.
- PR checks are green, branch is pushed, and PR is linked on the issue.
- Required PR metadata is present (`symphony` label).
- PR body follows the Test-First PR submission template and includes red/green evidence, commands run, test scope, agent usage, and reviewer checklist.
- `harness-quality-gate` and Superpowers skills (`test-driven-development`, `verification-before-completion`, E2E harness when UI-touching) are satisfied.
- If app-touching, runtime validation/media requirements from `App runtime validation (required)` are complete.

## Guardrails

- If the branch PR is already closed/merged, do not reuse that branch or prior implementation state for continuation.
- For closed/merged branch PRs, create a new branch from `origin/main` and restart from reproduction/planning as if starting fresh.
- If issue state is `Backlog` or `Blocked`, do not modify it; wait for human to move it to `Todo` or `Rework`.
- Do not edit the issue body/description for planning or progress tracking.
- Use exactly one persistent workpad comment (`## Claude Workpad`) per issue.
- If comment editing is unavailable in-session, use the update script. Only report blocked if both MCP editing and script-based editing are unavailable.
- Temporary proof edits are allowed only for local verification and must be reverted before commit.
- If out-of-scope improvements are found, create a separate Backlog issue rather
  than expanding current scope, and include a clear
  title/description/acceptance criteria, same-project assignment, a `related`
  link to the current issue, and `blockedBy` when the follow-up depends on the
  current issue.
- Do not move to `Agent Review` unless the `Completion bar before Agent Review` is satisfied.
- Do not move from `Rework` directly to `Human Review`; every rework attempt must return through `Agent Review` first.
- In `Human Review`, do not make changes; wait and poll.
- If state is terminal (`Done`) or blocked (`Blocked`), do nothing and shut down.
- Keep issue text concise, specific, and reviewer-oriented.
- If blocked and no workpad exists yet, add one blocker comment describing blocker, impact, and next unblock action.

## Workpad template

Use this exact structure for the persistent workpad comment and keep it updated in place throughout execution:

````md
## Claude Workpad

```text
<hostname>:<abs-path>@<short-sha>
```

### Plan

- [ ] 1\. Parent task
  - [ ] 1.1 Child task
  - [ ] 1.2 Child task
- [ ] 2\. Parent task

### Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2

### Test-first Evidence

- [ ] Red: `<failing test or executable validation before implementation>`
- [ ] Green: `<passing validation after implementation>`

### Commit Plan

- [ ] `test:` red test or documented exception
- [ ] `impl:`/`feat:` minimal behavior change
- [ ] optional `refactor:`/`docs:`/`chore:` cleanup

### Validation

- [ ] targeted tests: `<command>`

### Notes

- <short progress note with timestamp>

### Agent Review

- [ ] Status: `pending | changes requested | approved`
- Reviewer: `<agent/runtime or person>`
- Findings:
  - [ ] `<finding with file/line, risk, and required fix>`
- Verification requested:
  - [ ] `<command, check, or evidence the fixer must provide>`
- Resolution notes:
  - <how each finding was fixed or why it was explicitly declined>

### Confusions

- <only include when something was confusing during execution>
````
