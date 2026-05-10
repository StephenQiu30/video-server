## ADDED Requirements

### Requirement: Self-hosted download resilience
The system SHALL improve download task resilience for personal self-hosted use without adding new task states or platform-specific bypass logic.

#### Scenario: Download retries are conservative
- **WHEN** a Worker downloads a task through yt-dlp
- **THEN** the Worker uses bounded retry, fragment retry, timeout, and continue-download options
- **AND** the task still respects configured maximum file size and runtime limits

#### Scenario: Running task cancellation is observed
- **WHEN** a running task is canceled while yt-dlp is downloading
- **THEN** the Worker detects cancellation at progress checkpoints and stops processing without marking the task succeeded

#### Scenario: Task events explain progress
- **WHEN** a task is processed by the Worker
- **THEN** events record key stages including download start, media validation, upload, success, and failure reasons

### Requirement: Expired output cleanup command
The system SHALL provide a self-hosted command for cleaning expired output objects while preserving task history.

#### Scenario: Expired outputs cleaned
- **WHEN** the cleanup command runs
- **THEN** expired object storage files are removed
- **AND** task history remains available with an expired-file reason
