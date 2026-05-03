## MODIFIED Requirements

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
