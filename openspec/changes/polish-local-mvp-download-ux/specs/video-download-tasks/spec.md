## MODIFIED Requirements

### Requirement: Video URL parsing
The system SHALL accept a local user-submitted video URL, normalize common no-scheme domain URLs, and attempt to parse public video metadata through the download engine adapter.

#### Scenario: Public URL parsed
- **WHEN** the local user submits a supported public video URL
- **THEN** the system returns title, cover when available, duration when available, and available formats

#### Scenario: No-scheme URL normalized
- **WHEN** the local user submits a domain URL such as `example.com/video`
- **THEN** the system treats it as `https://example.com/video` before parsing or task creation

#### Scenario: Invalid URL rejected clearly
- **WHEN** the local user submits text that is not a valid HTTP or HTTPS URL
- **THEN** the system returns a user-understandable invalid URL reason

### Requirement: Download task state machine
The system SHALL represent download tasks using queued, running, succeeded, failed, and canceled states, and SHALL expose enough state for local MVP history and recovery actions.

#### Scenario: Task status query
- **WHEN** the local user queries an owned task
- **THEN** the system returns the current state, progress when available, and failure reason when failed

#### Scenario: Task list filtered for UI
- **WHEN** the local user queries task history with optional state or limit filters
- **THEN** the system returns matching owned tasks ordered from newest to oldest

### Requirement: Download task limits
The system SHALL enforce default resource limits of 2GB per task, 2 hours maximum runtime, 2 global concurrent downloads, 1 concurrent download per user, and 24 hours file retention.

#### Scenario: Limit exceeded
- **WHEN** a task exceeds a configured size, duration, concurrency, or retention limit
- **THEN** the system prevents, stops, or expires the task and returns a user-understandable reason

#### Scenario: Expired output cleaned but history retained
- **WHEN** a succeeded task output passes its retention time
- **THEN** the system may delete the stored file object
- **AND** the task history remains visible with an expired-file reason and retry path
