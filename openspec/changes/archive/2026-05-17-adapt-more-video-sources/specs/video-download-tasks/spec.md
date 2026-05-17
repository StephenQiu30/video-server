## MODIFIED Requirements

### Requirement: Video URL parsing
The system SHALL accept a local user-submitted video URL or a rich-text sharing description block containing a URL, automatically extract the clean URL via the link sanitizer, normalize common no-scheme domain URLs, and attempt to parse public video metadata through the download engine adapter.

#### Scenario: Public URL parsed
- **WHEN** the local user submits a supported public video URL
- **THEN** the system returns title, cover when available, duration when available, and available formats

#### Scenario: No-scheme URL normalized
- **WHEN** the local user submits a domain URL such as `example.com/video`
- **THEN** the system treats it as `https://example.com/video` before parsing or task creation

#### Scenario: Invalid URL rejected clearly
- **WHEN** the local user submits text that is not a valid HTTP or HTTPS URL, or contains no valid embedded URL
- **THEN** the system returns a user-understandable invalid URL reason
