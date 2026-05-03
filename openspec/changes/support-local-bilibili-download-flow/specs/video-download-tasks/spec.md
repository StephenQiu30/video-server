## ADDED Requirements

### Requirement: Local Bilibili download flow
The system SHALL support Bilibili download attempts for the local single-user MVP through the generic yt-dlp adapter.

#### Scenario: Public or locally accessible Bilibili URL parsed
- **WHEN** the local user submits a Bilibili video URL that yt-dlp can access
- **THEN** the system returns title, integer duration when available, cover when available, and a recommended download format

#### Scenario: Recommended format is available
- **WHEN** parsed formats contain separate video or audio streams
- **THEN** the user can choose a recommended combined format for download without manually selecting audio-only or video-only streams

#### Scenario: Bilibili parsing failure is understandable
- **WHEN** Bilibili parsing fails due to network, platform, or login-state problems
- **THEN** the system returns a Chinese failure reason instead of an internal server error

### Requirement: Local browser login state for worker downloads
The local Worker SHALL read the local user's browser login state for downloads when explicitly configured.

#### Scenario: Chrome login state used locally
- **WHEN** `YTDLP_COOKIES_FROM_BROWSER=chrome` is configured for the local Worker
- **THEN** the Worker passes Chrome browser login-state options to yt-dlp during download
- **AND** Cookie content is not accepted by API requests, stored in the database, returned to the frontend, or written to logs

#### Scenario: Browser login state unavailable
- **WHEN** the local Worker cannot read the configured browser login state
- **THEN** the task fails with a user-understandable browser login-state reason
