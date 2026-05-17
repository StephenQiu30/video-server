# link-sanitizer Specification

## Purpose
TBD - created by archiving change adapt-more-video-sources. Update Purpose after archive.
## Requirements
### Requirement: Input link sanitization
The system SHALL automatically parse the user-submitted video link input, identify any embedded HTTP or HTTPS URLs, and extract the first valid URL while discarding surrounding text, emojis, and promotional copy.

#### Scenario: Raw sharing text block parsed
- **WHEN** the user submits a text block containing emojis, Chinese promotional words, and a valid sharing URL (e.g., `【小猫咪】https://v.douyin.com/iJxxqxx/ 复制链接即可查看...`)
- **THEN** the system extracts `https://v.douyin.com/iJxxqxx/` and discards all other characters prior to validation and parsing

#### Scenario: Text without any URL rejected
- **WHEN** the user submits a text block containing no valid URL
- **THEN** the system rejects the input with a clear, user-understandable validation error

