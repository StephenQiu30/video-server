## MODIFIED Requirements

### Requirement: Current user identity
The system SHALL expose an authenticated current-user endpoint and display user identity in the frontend application when logged in.

#### Scenario: Current user query and header display
- **WHEN** a request includes a valid JWT access token
- **THEN** the system returns the authenticated user's identity (email, GitHub metadata, avatar)
- **AND** the frontend header SHALL display the user's avatar or display name instead of the "登录" and "立即开始" options
- **AND** the frontend header SHALL provide a dropdown menu for navigation and logout
