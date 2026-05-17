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
The system SHALL expose an authenticated current-user endpoint and display user identity in the frontend application when logged in.

#### Scenario: Current user query and header display
- **WHEN** a request includes a valid JWT access token
- **THEN** the system returns the authenticated user's identity (email, GitHub metadata, avatar)
- **AND** the frontend header SHALL display the user's avatar or display name instead of the "登录" and "立即开始" options
- **AND** the frontend header SHALL provide a dropdown menu for navigation and logout

### Requirement: Task ownership
The system SHALL associate each download task with the authenticated user who created it.

#### Scenario: User sees own tasks
- **WHEN** a user queries download tasks
- **THEN** the system returns only tasks owned by that user

### Requirement: Robust GitHub API Communication
The system SHALL ensure reliable communication with GitHub APIs by providing necessary identification and content negotiation headers.

#### Scenario: Communication with GitHub API
- **WHEN** the system makes a request to GitHub API (Token exchange or User info)
- **THEN** it SHALL include a `User-Agent` header (e.g., 'StephenVideo')
- **AND** it SHALL include an `Accept: application/json` header

### Requirement: OAuth Error Handling and Validation
The system SHALL validate responses from GitHub and handle errors gracefully to avoid internal crashes during the authentication flow.

#### Scenario: Handling non-JSON response from GitHub
- **WHEN** GitHub returns a response that is not valid JSON
- **THEN** the system SHALL catch the error
- **AND** return a clear `HTTP 400 Bad Request` or `HTTP 502 Bad Gateway` error to the client instead of a `500 Internal Server Error`
- **AND** log the response status and snippet of content for debugging

