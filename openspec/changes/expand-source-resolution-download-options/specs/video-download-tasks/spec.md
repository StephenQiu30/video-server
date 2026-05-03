## ADDED Requirements

### Requirement: Source-aware public URL parsing
The system SHALL expose the video source identified by the generic yt-dlp adapter when public URL parsing succeeds.

#### Scenario: Source identified
- **WHEN** the local user submits a public URL that yt-dlp can parse
- **THEN** the parse response includes the extractor and a user-facing source name when available
- **AND** the system does not use a platform-specific bypass parser

### Requirement: Resolution preset formats
The system SHALL provide user-friendly resolution presets for parsed videos when compatible source formats are available.

#### Scenario: Resolution presets returned
- **WHEN** parsed formats contain video heights
- **THEN** the system returns recommended, up to 1080p, up to 720p, up to 480p, and up to 360p format choices
- **AND** each downloadable preset uses a short yt-dlp selector that can be saved as the task format id

#### Scenario: Resolution preset unavailable
- **WHEN** a parsed source does not provide a compatible video format for a preset
- **THEN** the preset is marked unavailable or omitted from task creation
- **AND** the frontend does not imply that the missing quality can be downloaded

### Requirement: Best-effort multi-source support
The system SHALL treat Bilibili, Douyin, TikTok, XiaoHongShu, Ixigua, YouTube, Vimeo, Dailymotion, Weibo, and other yt-dlp extractors as best-effort public-source support in the local MVP.

#### Scenario: Public source unsupported or changed
- **WHEN** yt-dlp cannot parse or download a public URL because the platform is unsupported, changed, or inaccessible
- **THEN** the system returns a user-understandable failure reason
- **AND** the system does not request uploaded Cookies, bypass DRM, bypass paywalls, bypass member-only content, or promise universal support
