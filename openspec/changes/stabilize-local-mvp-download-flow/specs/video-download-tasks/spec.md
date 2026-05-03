## ADDED Requirements

### Requirement: Task events
The system SHALL expose task event history for local MVP task details.

#### Scenario: Task events queried
- **WHEN** the user opens a task detail view
- **THEN** the API returns ordered task events including state, message, and creation time

### Requirement: Task retry
The system SHALL allow failed, canceled, or expired local MVP tasks to be retried by creating a new queued task.

#### Scenario: Retry creates new task
- **WHEN** the user retries a failed, canceled, or expired task
- **THEN** the system creates a new queued task using the original URL, title, format, and metadata
- **AND** the original task remains unchanged for history and troubleshooting

## MODIFIED Requirements

### Requirement: Download task limits
The system SHALL enforce default resource limits of 2GB per task, 2 hours maximum runtime, 2 global concurrent downloads, 1 concurrent download per user, and 24 hours file retention.

#### Scenario: Limit exceeded
- **WHEN** a task exceeds a configured size, duration, concurrency, or retention limit
- **THEN** the system prevents, stops, or expires the task and returns a user-understandable reason

#### Scenario: Stale active task reconciled
- **WHEN** a queued or running task is older than the configured maximum runtime
- **THEN** the system marks it failed with a timeout reason so it no longer blocks concurrency
