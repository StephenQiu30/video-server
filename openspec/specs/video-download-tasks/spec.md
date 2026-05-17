# video-download-tasks Specification

## Purpose
TBD - created by archiving change bootstrap-mvp-foundation. Update Purpose after archive.
## Requirements
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

### Requirement: Download task creation
The system SHALL allow an authenticated user to create a download task from a parsed video and selected format.

#### Scenario: Task created
- **WHEN** a user selects a valid downloadable format
- **THEN** the system creates a queued download task owned by that user

### Requirement: Download task state machine
The system SHALL represent download tasks using queued, running, succeeded, failed, and canceled states, and SHALL expose enough state for local MVP history and recovery actions.

#### Scenario: Task status query
- **WHEN** the local user queries an owned task
- **THEN** the system returns the current state, progress when available, and failure reason when failed

#### Scenario: Task list filtered for UI
- **WHEN** the local user queries task history with optional state or limit filters
- **THEN** the system returns matching owned tasks ordered from newest to oldest

### Requirement: Download task limits
The system SHALL enforce default resource limits of 2GB per task, 2 hours maximum runtime, 2 global concurrent downloads, 1 concurrent download per user, and 24 hours file retention.

#### Scenario: Limit exceeded
- **WHEN** a task exceeds a configured size, duration, concurrency, or retention limit
- **THEN** the system prevents, stops, or expires the task and returns a user-understandable reason

#### Scenario: Stale active task reconciled
- **WHEN** a queued or running task is older than the configured maximum runtime
- **THEN** the system marks it failed with a timeout reason so it no longer blocks concurrency

### Requirement: Task cancellation
The system SHALL allow a user to cancel their own queued or running download task.

#### Scenario: Task canceled
- **WHEN** a user cancels an owned queued or running task
- **THEN** the system transitions the task to canceled and stops further processing where possible

### Requirement: No platform-specific parsing in MVP
The system SHALL NOT implement platform-specific parsers in M1 and SHALL route parsing through the default download engine adapter.

#### Scenario: Unsupported platform
- **WHEN** the default download engine cannot parse a URL
- **THEN** the system returns an unsupported or parse-failed reason without attempting a custom platform bypass

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

#### Scenario: Resolution selected before task creation
- **WHEN** parsing succeeds and resolution presets are available
- **THEN** the frontend requires the user to select one preset before creating the download task
- **AND** task creation uses the selected preset selector instead of silently using the recommended format

### Requirement: Best-effort multi-source support
The system SHALL treat Bilibili, Douyin, TikTok, XiaoHongShu, Ixigua, YouTube, Vimeo, Dailymotion, Weibo, and other yt-dlp extractors as best-effort public-source support in the local MVP.

#### Scenario: Public source unsupported or changed
- **WHEN** yt-dlp cannot parse or download a public URL because the platform is unsupported, changed, or inaccessible
- **THEN** the system returns a user-understandable failure reason
- **AND** the system does not request uploaded Cookies, bypass DRM, bypass paywalls, bypass member-only content, or promise universal support

### Requirement: Explicit retry chain

The system SHALL preserve retry attempts as separate task records while linking each retry to the previous attempt.

#### Scenario: Failed task retried
- **WHEN** a failed or canceled task is retried
- **THEN** the system creates a new queued task with `retry_of_task_id` pointing to the previous task and `attempt_no` incremented by one
- **AND** the previous task remains available in history

#### Scenario: Non-retryable task rejected
- **WHEN** a queued or running task is retried
- **THEN** the system rejects the request with a user-understandable conflict error

#### Scenario: Superseded attempt rejected
- **WHEN** a task already has a newer retry attempt
- **THEN** the system rejects another retry from the old attempt and asks the user to operate on the latest task

### Requirement: Retry-aware task presentation

The system SHALL identify whether a task is the latest attempt in its retry chain.

#### Scenario: Latest attempt marked
- **WHEN** tasks are listed or queried
- **THEN** each task includes retry metadata and whether it is the latest attempt

#### Scenario: Workspace hides superseded attempts
- **WHEN** the workspace renders key tasks
- **THEN** superseded retry attempts are not shown in the primary task area
- **AND** full task history still includes all attempts

### Requirement: Self-hosted download resilience
The system SHALL improve download task resilience for personal self-hosted use without adding new task states or platform-specific bypass logic.

#### Scenario: Download retries are conservative
- **WHEN** a Worker downloads a task through yt-dlp
- **THEN** the Worker uses bounded retry, fragment retry, timeout, and continue-download options
- **AND** the task still respects configured maximum file size and runtime limits

#### Scenario: Running task cancellation is observed
- **WHEN** a running task is canceled while yt-dlp is downloading
- **THEN** the Worker detects cancellation at progress checkpoints and stops processing without marking the task succeeded

#### Scenario: Task events explain progress
- **WHEN** a task is processed by the Worker
- **THEN** events record key stages including download start, media validation, upload, success, and failure reasons

### Requirement: Expired output cleanup command
The system SHALL provide a self-hosted command for cleaning expired output objects while preserving task history.

#### Scenario: Expired outputs cleaned
- **WHEN** the cleanup command runs
- **THEN** expired object storage files are removed
- **AND** task history remains available with an expired-file reason

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

### Requirement: Task events
The system SHALL expose task event history for local MVP task details.

#### Scenario: Task events queried
- **WHEN** the user opens a task detail view
- **THEN** the API returns ordered task events including state, message, and creation time

### Requirement: Task retry
The system SHALL allow failed, canceled, or expired local MVP tasks to be retried by creating a new queued task.

#### Scenario: Retry creates new task
- **WHEN** the user retries a failed, canceled, or expired task
- **THEN** the system creates a new queued task using the original URL, title, format, and metadata
- **AND** the original task remains unchanged for history and troubleshooting

