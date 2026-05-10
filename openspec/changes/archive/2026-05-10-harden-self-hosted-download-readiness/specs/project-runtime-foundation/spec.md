## ADDED Requirements

### Requirement: Self-hosted readiness diagnostics
The system SHALL expose self-hosted readiness diagnostics for core local dependencies.

#### Scenario: Runtime checks are visible
- **WHEN** `/ready` is requested
- **THEN** the response reports database, Redis, queue, object storage, media tools, and download work directory checks

### Requirement: Self-hosted smoke
The system SHALL provide a self-hosted smoke script for the personal deployment download path.

#### Scenario: Smoke verifies core path
- **WHEN** the self-hosted smoke script runs against a started local deployment
- **THEN** it verifies health, readiness, task creation, unfinished download-link rejection, successful small-file download, forged signature rejection, and cleanup entrypoints
