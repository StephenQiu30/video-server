# user-auth Specification

## Purpose
TBD - created by archiving change bootstrap-mvp-foundation. Update Purpose after archive.
## Requirements
### Requirement: User registration
The system SHALL allow users to register with credentials for the MVP JWT user system.

#### Scenario: Successful registration
- **WHEN** a new user submits valid registration credentials
- **THEN** the system creates the user and returns an authentication result or allows immediate login

### Requirement: User login
The system SHALL allow registered users to log in and receive a JWT access token.

#### Scenario: Successful login
- **WHEN** a registered user submits valid credentials
- **THEN** the system returns a JWT access token usable for authenticated API requests

### Requirement: Current user identity
The system SHALL expose an authenticated current-user endpoint.

#### Scenario: Current user query
- **WHEN** a request includes a valid JWT access token
- **THEN** the system returns the authenticated user's identity and basic profile fields

### Requirement: Task ownership
The system SHALL associate each download task with the authenticated user who created it.

#### Scenario: User sees own tasks
- **WHEN** a user queries download tasks
- **THEN** the system returns only tasks owned by that user

