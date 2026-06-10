# Presigned Download Delivery

## Purpose

Define the normative requirements for presigned download URL generation, expiration cleanup, and error semantics for the video-server download delivery pipeline.

## Requirements

### Requirement: Download Link MUST Be a Short-Lived Presigned URL
The `GET /api/tasks/{task_id}/download-link` endpoint MUST return a presigned S3 URL with a configurable TTL (default 900 seconds).

#### Scenario: Owner requests download link for succeeded task
- **GIVEN** a task is in `SUCCEEDED` state with a valid `object_key` and unexpired `expires_at`
- **WHEN** the owner requests the download link
- **THEN** the response MUST contain a `url` field with a presigned S3 URL
- **AND** the response MUST contain an `expires_in_seconds` field with the TTL value
- **AND** the URL MUST be generated against the public S3 endpoint

### Requirement: Download Link MUST Reject Non-Succeeded Tasks
Requesting a download link for a task not in `SUCCEEDED` state MUST return HTTP 409 with error code `invalid_state`.

#### Scenario: Task is still running
- **GIVEN** a task is in `RUNNING` state
- **WHEN** the owner requests the download link
- **THEN** the response MUST be HTTP 409
- **AND** the error code MUST be `invalid_state`

### Requirement: Download Link MUST Reject Expired or Missing Artifacts
Requesting a download link for a task with null `object_key` or past `expires_at` MUST return HTTP 410 with error code `retention_expired`.

#### Scenario: Artifact has expired
- **GIVEN** a succeeded task has `expires_at` in the past
- **WHEN** the owner requests the download link
- **THEN** the response MUST be HTTP 410
- **AND** the error code MUST be `retention_expired`

#### Scenario: Object key is null after cleanup
- **GIVEN** a succeeded task has `object_key = NULL` (post-cleanup)
- **WHEN** the owner requests the download link
- **THEN** the response MUST be HTTP 410
- **AND** the error code MUST be `retention_expired`

### Requirement: Expiration Cleanup MUST Preserve Task Record
When `cleanup_expired_task_outputs()` runs, it MUST delete the MinIO object, nullify `object_key`, set `failure_code = "retention_expired"`, but MUST keep the task in `SUCCEEDED` state.

#### Scenario: Cleanup processes an expired task
- **GIVEN** a succeeded task has `expires_at` in the past and `object_key` is not null
- **WHEN** `cleanup_expired_task_outputs()` runs
- **THEN** the MinIO object MUST be deleted
- **AND** `object_key` MUST be set to NULL
- **AND** `failure_code` MUST be set to `"retention_expired"`
- **AND** `failure_reason` MUST describe the expiration
- **AND** the task `state` MUST remain `SUCCEEDED`
- **AND** a `TaskEvent` MUST be recorded for the cleanup action

#### Scenario: Task detail returns after cleanup
- **GIVEN** a task has been cleaned up by the expiration process
- **WHEN** the client requests task detail via `GET /api/tasks/{task_id}`
- **THEN** the response MUST return HTTP 200 (not 404)
- **AND** the response MUST include `failure_code = "retention_expired"`
- **AND** the task `state` MUST still be `SUCCEEDED`

### Requirement: Cleanup MUST Be Triggered on Read Operations
`cleanup_expired_task_outputs()` MUST be called before listing tasks, streaming tasks, and requesting download links.

#### Scenario: Cleanup runs on task list
- **GIVEN** expired tasks exist in the database
- **WHEN** the client requests the task list
- **THEN** `cleanup_expired_task_outputs()` MUST be invoked before returning results

### Requirement: Cross-User Access MUST Be Rejected
Download link requests from non-owners MUST return HTTP 404.

#### Scenario: Attacker requests another user's download link
- **GIVEN** a task belongs to user A
- **WHEN** user B requests the download link
- **THEN** the response MUST be HTTP 404 with error code `not_found`

### Requirement: Presigned URL TTL MUST Be Configurable
The presigned URL TTL MUST be configurable via the `PRESIGNED_URL_TTL_SECONDS` environment variable (default: 900).

#### Scenario: Custom TTL configured
- **GIVEN** `PRESIGNED_URL_TTL_SECONDS=600`
- **WHEN** a presigned URL is generated
- **THEN** the URL MUST expire in 600 seconds

## Validation

- `npm test` runs `apps/api/tests/test_task_endpoints.py` which covers presigned URL generation, expiration cleanup, cross-user rejection, and error semantics.
- Manual inspection of `apps/api/app/services/storage.py` confirms `presign_download_url()` uses `public=True` endpoint and configurable TTL.
- Manual inspection of `apps/api/app/services/tasks.py` confirms `cleanup_expired_task_outputs()` nullifies `object_key`, sets `failure_code`, and preserves `state`.
