## ADDED Requirements

### Requirement: Live task progress stream

The system SHALL provide a lightweight server-to-browser task progress stream for the local MVP.

#### Scenario: Task stream emits snapshots
- **WHEN** the web client subscribes to the task stream
- **THEN** the API returns `text/event-stream` events containing recent task snapshots
- **AND** progress, state, failure reason, and output file fields update without requiring manual refresh

#### Scenario: Stream remains lightweight
- **WHEN** the task stream is open
- **THEN** it performs read-only short-lived database access per snapshot
- **AND** it does not run cleanup routines or hold long-lived database sessions

#### Scenario: Stream fallback
- **WHEN** the stream connection fails
- **THEN** the web client keeps the existing manual refresh path and may fall back to lightweight polling
