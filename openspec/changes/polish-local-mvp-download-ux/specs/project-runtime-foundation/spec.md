## ADDED Requirements

### Requirement: Local MVP download workspace feedback
The local MVP workspace SHALL provide visible feedback for parse, task creation, download, retry, and cancel actions.

#### Scenario: Invalid URL shows user feedback
- **WHEN** the local user submits an empty or invalid video URL
- **THEN** the web UI shows a Chinese error message instead of failing silently

#### Scenario: Action state is visible
- **WHEN** a parse, create, download, retry, or cancel action is in progress
- **THEN** the related control shows a loading or disabled state until the action completes

### Requirement: Workspace focuses on current work
The local MVP workspace SHALL focus on creating downloads and showing a small set of current or recent user-relevant tasks.

#### Scenario: Full history is separated
- **WHEN** the local user opens the workspace
- **THEN** the workspace does not make the full historical task list the primary content
- **AND** the full persistent history remains available from the task history page

#### Scenario: Smoke tasks do not dominate workspace
- **WHEN** smoke or negative test tasks exist in persistent history
- **THEN** they are not shown as prominent workspace tasks by default
