# video-download-tasks Specification

## Purpose
TBD - created by archiving change bootstrap-mvp-foundation. Update Purpose after archive.
## Requirements
### Requirement: Video URL parsing
The system SHALL accept a user-submitted video URL and attempt to parse public video metadata through the download engine adapter.

#### Scenario: Public URL parsed
- **WHEN** an authenticated user submits a supported public video URL
- **THEN** the system returns title, cover when available, duration when available, and available formats

### Requirement: Download task creation
The system SHALL allow an authenticated user to create a download task from a parsed video and selected format.

#### Scenario: Task created
- **WHEN** a user selects a valid downloadable format
- **THEN** the system creates a queued download task owned by that user

### Requirement: Download task state machine
The system SHALL represent download tasks using queued, running, succeeded, failed, and canceled states.

#### Scenario: Task status query
- **WHEN** a user queries an owned task
- **THEN** the system returns the current state, progress when available, and failure reason when failed

### Requirement: Download task limits
The system SHALL enforce default resource limits of 2GB per task, 2 hours maximum runtime, 2 global concurrent downloads, 1 concurrent download per user, and 24 hours file retention.

#### Scenario: Limit exceeded
- **WHEN** a task exceeds a configured size, duration, concurrency, or retention limit
- **THEN** the system prevents or stops the task and returns a user-understandable reason

### Requirement: Task cancellation
The system SHALL allow a user to cancel their own queued or running download task.

#### Scenario: Task canceled
- **WHEN** a user cancels an owned queued or running task
- **THEN** the system transitions the task to canceled and stops further processing where possible

### Requirement: No platform-specific parsing in MVP
The system SHALL NOT implement platform-specific parsers in M1 and SHALL route parsing through the default download engine adapter.

#### Scenario: Unsupported platform
- **WHEN** the default download engine cannot parse a URL
- **THEN** the system returns an unsupported or parse-failed reason without attempting a custom platform bypass

