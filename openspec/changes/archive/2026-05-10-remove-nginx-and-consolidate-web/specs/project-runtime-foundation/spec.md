## MODIFIED Requirements

### Requirement: Full stack Docker environment
#### Scenario: Consolidated API and Web
- **WHEN** the developer runs the application in Docker
- **THEN** the API container SHALL serve both the backend API endpoints and the frontend static assets
- **AND** the separate Nginx-based `web` service SHALL be removed to reduce overhead
