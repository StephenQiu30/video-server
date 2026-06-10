## ADDED Requirements

### Requirement: Object Key Pattern MUST Follow User-Scoped Convention
All artifacts uploaded to MinIO MUST use the key pattern `users/{user_id}/tasks/{task_id}/{filename}`.

#### Scenario: Successful download generates correct object key
- **GIVEN** a download task is assigned to user 42 with task ID `abc-123`
- **WHEN** the worker uploads the downloaded video file
- **THEN** the object key MUST be `users/42/tasks/abc-123/{filename}`
- **AND** the key MUST NOT contain date-based segments like `downloads/{yyyy}/{mm}/{dd}/`

### Requirement: Artifact Upload MUST Persist to MinIO
The worker MUST upload the primary video file to MinIO via `ObjectStorage.upload_file()` before marking the task as `SUCCEEDED`.

#### Scenario: Worker completes download and uploads artifact
- **GIVEN** yt-dlp has downloaded the video to a local working directory
- **WHEN** the worker finalizes the download
- **THEN** the file MUST be uploaded to MinIO with `content_type` set appropriately
- **AND** the `object_key`, `object_size`, and `expires_at` fields MUST be set on the `DownloadTask` record

#### Scenario: MinIO upload failure
- **GIVEN** the MinIO service is unreachable or returns an error
- **WHEN** the worker attempts to upload the artifact
- **THEN** the task MUST transition to `FAILED` state
- **AND** the `failure_code` MUST indicate the storage failure

### Requirement: Database Index MUST Track Artifact Location
The `download_tasks` table MUST store `object_key` (Text), `object_size` (BigInteger), and `expires_at` (DateTime) fields directly on the task record.

#### Scenario: Task record stores artifact metadata
- **GIVEN** a task has been successfully processed
- **WHEN** the task record is queried
- **THEN** `object_key` contains the MinIO object path
- **AND** `object_size` contains the file size in bytes
- **AND** `expires_at` contains the UTC timestamp when the file will be cleaned up

### Requirement: Task Detail MUST Return Metadata Completeness
The `GET /api/tasks/{task_id}` endpoint MUST return `title`, `cover_url`, `duration_seconds`, `object_size`, `output_filename`, and `expires_at` for succeeded tasks.

#### Scenario: Succeeded task exposes full metadata
- **GIVEN** a task has state `SUCCEEDED` with populated metadata fields
- **WHEN** the client requests task detail
- **THEN** the response MUST include `title`, `cover_url`, `duration_seconds`, `object_size`, `output_filename`, and `expires_at`

### Requirement: Cover URL is Optional and MUST NOT Block Success
If the cover image is unavailable, the task MUST still succeed. The `cover_url` field MAY be null.

#### Scenario: Cover unavailable but video succeeds
- **GIVEN** the platform does not provide a cover image
- **WHEN** the download completes successfully
- **THEN** the task state MUST be `SUCCEEDED`
- **AND** `cover_url` MUST be null or absent
