# user-auth Specification

## Purpose
Provide a secure and simplified authentication system using GitHub OAuth2 to manage user identities and access control.

## Requirements

### Requirement: GitHub OAuth Authentication
The system SHALL support user authentication via GitHub OAuth2.

#### Scenario 1: First-time GitHub Login (Silent Registration)
- **WHEN** a user successfully authenticates via GitHub OAuth
- **AND** the system does not recognize the GitHub UID
- **THEN** the system SHOULD automatically create a new user profile using GitHub info (email, name, avatar)
- **AND** issue a JWT access token

#### Scenario 2: Returning GitHub Login
- **WHEN** a known user authenticates via GitHub
- **THEN** the system SHOULD issue a JWT access token linked to the existing account

### Requirement: Current user identity
The system SHALL expose an authenticated current-user endpoint.

#### Scenario: Current user query
- **WHEN** a request includes a valid JWT access token
- **THEN** the system returns the authenticated user's identity (email, GitHub metadata, avatar)

### Requirement: Task ownership
The system SHALL associate each download task with the authenticated user who created it.

#### Scenario: User sees own tasks
- **WHEN** a user queries download tasks
- **THEN** the system returns only tasks owned by that user
