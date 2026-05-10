# project-runtime-foundation Specification

## Purpose
TBD - created by archiving change bootstrap-mvp-foundation. Update Purpose after archive.
## Requirements
### Requirement: Monorepo project layout
The system SHALL use the default recommended monorepo layout with separate web, API, worker, shared contract, and infrastructure directories.

#### Scenario: Project directories exist
- **WHEN** the M1 scaffold is created
- **THEN** the repository contains `apps/web`, `apps/api`, `apps/worker`, `packages/shared`, and `infra/docker`

### Requirement: Local and Docker runtime modes
The system SHALL support a local development runtime that can reuse existing Python, PostgreSQL, Redis, and MinIO / S3 services, and SHALL keep Docker Compose as a deployment or isolated-runtime option.

#### Scenario: Local backend starts without Docker
- **WHEN** a developer has local Python, PostgreSQL, Redis, and MinIO / S3 available
- **THEN** the documented local scripts start the API and worker without requiring Docker

#### Scenario: Docker API/Web with local Worker starts
- **WHEN** the local single-user download workflow is started with the root start command
- **THEN** Docker Compose starts API and Web
- **AND** a host Worker process is started once so yt-dlp can access host browser login state when configured

#### Scenario: Local Worker stops cleanly
- **WHEN** the root stop command is executed
- **THEN** Docker API/Web are stopped
- **AND** the host Worker process started by the project is stopped and its PID file is cleaned up

### Requirement: Environment configuration template
The system SHALL provide separate environment templates for local development, Docker deployment, and production deployment.

#### Scenario: Environment template is complete
- **WHEN** a developer chooses a runtime mode
- **THEN** the corresponding template contains all required keys for API, worker, database, Redis, object storage, JWT, and download limit settings

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

### Requirement: Native Ant Design Pro MVP workspace
The web application SHALL use native Ant Design Pro and Pro Components patterns for the M1 local workspace.

#### Scenario: Local workspace viewed
- **WHEN** a user opens the homepage, workspace, task history, or compliance page
- **THEN** the page is usable without login and uses standard Pro layout, cards, tables, forms, descriptions, and timelines rather than custom marketing visuals

