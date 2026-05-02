## ADDED Requirements

### Requirement: Monorepo project layout
The system SHALL use the default recommended monorepo layout with separate web, API, worker, shared contract, and infrastructure directories.

#### Scenario: Project directories exist
- **WHEN** the M1 scaffold is created
- **THEN** the repository contains `apps/web`, `apps/api`, `apps/worker`, `packages/shared`, and `infra/docker`

### Requirement: Docker Compose local runtime
The system SHALL provide a Docker Compose based local runtime for the web app, API, worker, PostgreSQL, Redis, and MinIO.

#### Scenario: Local stack starts
- **WHEN** a developer runs the documented Docker Compose startup command
- **THEN** the required services start with consistent network, volume, and environment configuration

### Requirement: Environment configuration template
The system SHALL provide an environment template for API, worker, database, Redis, object storage, JWT, and download limit settings.

#### Scenario: Environment template is complete
- **WHEN** a developer copies the environment template
- **THEN** the copied file contains all required keys to run the local stack without guessing missing variables
