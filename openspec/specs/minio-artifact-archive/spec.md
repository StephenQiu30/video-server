# MinIO Artifact Archive & Download Delivery

## Purpose

Define the normative requirements for MinIO object storage, artifact indexing, presigned download links, and expiration cleanup in the video-server project.

## Requirements

### Requirement: Object Key Pattern
The system MUST use a stable, user-scoped object key pattern for all MinIO artifacts.

#### Scenario: Successful upload creates predictable key
- **GIVEN** a download task with `id=550e8400-e29b-41d4-a716-446655440000` and `user_id=1`
- **WHEN** the Worker uploads the video file `video.mp4`
- **THEN** the MinIO object key SHALL be `users/1/tasks/550e8400-e29b-41d4-a716-446655440000/video.mp4`
- **AND** the key pattern SHALL be `users/{user_id}/tasks/{task_id}/{filename}`

#### Scenario: Object key is immutable after write
- **GIVEN** a task has been uploaded with a specific object key
- **WHEN** the task record is queried
- **THEN** the `object_key` field SHALL remain unchanged until expiration cleanup

### Requirement: Artifact Index on DownloadTask
The system MUST store artifact index fields directly on the `download_tasks` table.

#### Scenario: Task record contains artifact metadata
- **GIVEN** a download task has successfully uploaded to MinIO
- **WHEN** the task state is updated to `succeeded`
- **THEN** the `download_tasks` record SHALL contain:
  - `object_key` (Text): MinIO object path
  - `object_size` (BigInteger): file size in bytes
  - `output_filename` (String 255): original filename for Content-Disposition
  - `expires_at` (DateTime with timezone): artifact expiration time

#### Scenario: No separate artifacts table
- **GIVEN** the current implementation
- **WHEN** artifact data is stored
- **THEN** the system SHALL NOT use a separate `task_artifacts` table
- **AND** all artifact metadata SHALL be stored as columns on `download_tasks`

### Requirement: Presigned Download URL
The system MUST generate short-lived presigned URLs for artifact download.

#### Scenario: Download link request returns presigned URL
- **GIVEN** a succeeded task with valid `object_key` and future `expires_at`
- **WHEN** `GET /api/tasks/{task_id}/download-link` is requested
- **THEN** the response SHALL contain a presigned URL
- **AND** the URL SHALL expire after `presigned_url_ttl_seconds` (default 900 seconds)

#### Scenario: Presigned URL uses public endpoint
- **GIVEN** `s3_public_endpoint_url` is configured
- **WHEN** a presigned URL is generated
- **THEN** the URL SHALL use `s3_public_endpoint_url` as the base
- **AND** the URL SHALL be accessible to the client

### Requirement: Expiration Cleanup
The system MUST clean up expired artifacts while preserving task history.

#### Scenario: Expired artifact cleanup on query
- **GIVEN** a succeeded task where `expires_at <= now` and `object_key IS NOT NULL`
- **WHEN** task list or download link is requested
- **THEN** the system SHALL delete the MinIO object
- **AND** set `object_key = None`
- **AND** set `failure_code = "retention_expired"`
- **AND** preserve the task record with `state = "succeeded"`

#### Scenario: Expired task returns appropriate error
- **GIVEN** a task where `object_key` is `None` or `expires_at <= now`
- **WHEN** `GET /api/tasks/{task_id}/download-link` is requested
- **THEN** the response SHALL return HTTP 410 with `retention_expired` error

### Requirement: Retention Duration
The system MUST support configurable artifact retention.

#### Scenario: Default retention is 24 hours
- **GIVEN** a user with `file_retention_hours = 24` (default)
- **WHEN** an artifact is uploaded
- **THEN** `expires_at` SHALL be `now + 24 hours`

#### Scenario: User-level retention override
- **GIVEN** a user with `file_retention_hours = 48`
- **WHEN** an artifact is uploaded
- **THEN** `expires_at` SHALL be `now + 48 hours`

### Requirement: MinIO Configuration
The system MUST support configurable MinIO connection settings.

#### Scenario: Required configuration
- **GIVEN** the MinIO storage service
- **WHEN** the system starts
- **THEN** the following configuration SHALL be available:
  - `s3_endpoint_url`: internal MinIO address
  - `s3_public_endpoint_url`: client-facing MinIO address for presigned URLs
  - `s3_access_key_id` and `s3_secret_access_key`: authentication credentials
  - `s3_bucket`: storage bucket name (default `video-downloads`)
  - `s3_region`: region identifier
  - `s3_force_path_style`: path-style addressing (required for MinIO)

## Validation

### Validation: Repository structure
- `openspec/specs/minio-artifact-archive/spec.md` exists
- `openspec/config.yaml` exists

### Validation: Implementation alignment
- Object key pattern in `apps/worker/worker/artifact_storage.py` matches `users/{user_id}/tasks/{task_id}/{filename}`
- Artifact fields in `apps/api/app/models.py` DownloadTask match the spec
- Presigned URL logic in `apps/api/app/services/storage.py` uses `presigned_url_ttl_seconds`
- Expiration cleanup in `apps/api/app/services/tasks.py` sets `failure_code = "retention_expired"`

### Validation: Test coverage
- `apps/api/tests/test_task_endpoints.py` covers download link and expired link scenarios
- `apps/api/tests/test_worker_jobs.py` covers upload flow
