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

#### Scenario: Docker deployment stack is configured
- **WHEN** a developer chooses the Docker deployment path
- **THEN** Docker Compose provides consistent network, volume, and environment configuration for API, worker, PostgreSQL, Redis, and MinIO

### Requirement: Environment configuration template
The system SHALL provide separate environment templates for local development, Docker deployment, and production deployment.

#### Scenario: Environment template is complete
- **WHEN** a developer chooses a runtime mode
- **THEN** the corresponding template contains all required keys for API, worker, database, Redis, object storage, JWT, and download limit settings

