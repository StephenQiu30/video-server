# production-deployment-baseline Specification

## Purpose
TBD - created by archiving change production-saas-readiness. Update Purpose after archive.
## Requirements
### Requirement: Single-machine Compose deployment
The system SHALL provide a single-machine Docker Compose deployment baseline for the beta SaaS environment.

#### Scenario: Compose stack starts
- **WHEN** production deployment is executed on a prepared server
- **THEN** Web, API, Worker, PostgreSQL, Redis, and MinIO services can be started through the documented Compose workflow

### Requirement: Nginx HTTPS entrypoint
The system SHALL use Nginx as the first beta production HTTPS entrypoint.

#### Scenario: HTTPS request routed
- **WHEN** a user accesses the production domain over HTTPS
- **THEN** Nginx routes frontend and API requests to the correct internal services

### Requirement: Production environment safety
The system SHALL require production secrets and public URLs to be explicitly configured before release.

#### Scenario: Unsafe defaults rejected
- **WHEN** production configuration still uses example secrets, empty passwords, or local development defaults
- **THEN** the deployment is not accepted for release

### Requirement: Backup and cleanup operations
The system SHALL document backup, restore, persistence, and cleanup expectations for PostgreSQL, Redis, MinIO, and temporary download files.

#### Scenario: Operator follows recovery documentation
- **WHEN** an operator needs to restore data or clean expired files
- **THEN** the documentation provides the required commands or operational steps

