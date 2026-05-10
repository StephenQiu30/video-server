# Specification Delta: project-runtime-foundation

## MODIFIED Requirements

### Requirement: Monorepo project layout
#### Scenario: Project directories exist
- **WHEN** the M1 scaffold is created
- **THEN** the repository contains `apps/web`, `apps/api`, `apps/worker`, and `packages/shared`
- **AND** Docker-related configurations are unified in the project root

### Requirement: Local and Docker runtime modes
#### Scenario: Infrastructure-only Docker environment
- **WHEN** a developer runs `docker compose up` in the root
- **THEN** only core infrastructure services (PostgreSQL, Redis, MinIO) are started
- **AND** the application code can be run directly on the host machine for development

#### Scenario: Full stack Docker environment
- **WHEN** a developer runs `docker compose -f docker-compose.prod.yml up`
- **THEN** the entire application stack (API, Worker, Web) and its infrastructure are started using production-ready Docker images
