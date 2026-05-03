## ADDED Requirements

### Requirement: Explicit retry chain

The system SHALL preserve retry attempts as separate task records while linking each retry to the previous attempt.

#### Scenario: Failed task retried
- **WHEN** a failed or canceled task is retried
- **THEN** the system creates a new queued task with `retry_of_task_id` pointing to the previous task and `attempt_no` incremented by one
- **AND** the previous task remains available in history

#### Scenario: Non-retryable task rejected
- **WHEN** a queued or running task is retried
- **THEN** the system rejects the request with a user-understandable conflict error

#### Scenario: Superseded attempt rejected
- **WHEN** a task already has a newer retry attempt
- **THEN** the system rejects another retry from the old attempt and asks the user to operate on the latest task

### Requirement: Retry-aware task presentation

The system SHALL identify whether a task is the latest attempt in its retry chain.

#### Scenario: Latest attempt marked
- **WHEN** tasks are listed or queried
- **THEN** each task includes retry metadata and whether it is the latest attempt

#### Scenario: Workspace hides superseded attempts
- **WHEN** the workspace renders key tasks
- **THEN** superseded retry attempts are not shown in the primary task area
- **AND** full task history still includes all attempts
