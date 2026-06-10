# Agent Governance

## Purpose

Define the accepted long-lived governance baseline for the video-server repository, including how OpenSpec-driven SDD execution, multi-agent entrypoints, project boundaries, Agent Review, and repository validation work together.

## Requirements

### Requirement: OpenSpec Baseline Must Exist
The repository MUST keep an OpenSpec baseline under `openspec/specs/` for long-lived governance and workflow requirements.

#### Scenario: Fresh clone inspects normative assets
- **GIVEN** a contributor clones the repository
- **WHEN** the contributor reviews the normative files
- **THEN** the repository includes `openspec/config.yaml`
- **AND** the repository includes at least one tracked spec under `openspec/specs/`
- **AND** those files describe the accepted governance baseline

### Requirement: SDD Updates Must Precede Normative Changes
Any change that alters long-lived behavior, contracts, review gates, or role responsibilities MUST update OpenSpec specs before the corresponding implementation or normative rewrite is considered complete.

#### Scenario: Governance rule changes
- **GIVEN** a change modifies `CLAUDE.md`, `WORKFLOW.md`, role definitions, or validation expectations
- **WHEN** the change affects durable repository behavior
- **THEN** the change creates or updates proposal/specs/design/tasks under `openspec/changes/` before implementation
- **AND** the accepted result is eventually synchronized back into `openspec/specs/`

### Requirement: Agent Review Must Validate Against OpenSpec
Agent Review MUST compare the delivered implementation against the linked OpenSpec change artifacts and baseline specs before the task can move to Human Review.

#### Scenario: Review checks for drift
- **GIVEN** a task enters `Agent Review`
- **WHEN** the reviewer validates the task
- **THEN** the reviewer compares implementation, workpad, PR evidence, and validation output against the current OpenSpec proposal/specs/design/tasks
- **AND** any missing requirement, scope drift, or over-implementation is treated as a review failure

### Requirement: Claude Entrypoint Must Exist
The repository MUST keep the Claude governance entrypoint as the single agent standards source.

#### Scenario: Contributor inspects agent entrypoints
- **GIVEN** a contributor reviews repository governance files
- **WHEN** the contributor checks agent configuration
- **THEN** `CLAUDE.md` and `CLAUDE.local.md` are present
- **AND** `.claude/agents/` and `.claude/skills/` remain available
- **AND** legacy Codex or Cursor governance entrypoints are not required

### Requirement: Tests Must Stay Inside Accepted Boundary
The repository MUST reject compatibility-only tests and MUST keep automated checks aligned to the current accepted project boundary.

#### Scenario: Compatibility fallback test is proposed
- **GIVEN** a change adds tests for legacy fallback behavior, dual-track compatibility, or unaccepted historical branches
- **WHEN** that behavior is not explicitly required by the repository norms
- **THEN** the change is treated as out of scope
- **AND** the compatibility-only test is not part of the accepted baseline

### Requirement: Validation Must Check OpenSpec Assets
Repository validation MUST fail when the required OpenSpec baseline or OpenSpec skills are missing.

#### Scenario: Required OpenSpec asset removed
- **GIVEN** `openspec/config.yaml`, `openspec/specs/agent-governance/spec.md`, or required `.claude/skills/openspec-*` skill files are missing
- **WHEN** `bash scripts/validate-repository.sh` runs
- **THEN** `scripts/validate-repository.sh` fails
- **AND** the repository is not considered ready for review
