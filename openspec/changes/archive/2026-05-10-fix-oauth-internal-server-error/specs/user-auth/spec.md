## ADDED Requirements

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
