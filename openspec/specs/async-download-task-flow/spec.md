# Async Download Task Flow

## Purpose

Define the async download task lifecycle, state machine, failure semantics, cancel/retry boundaries, and API contracts for the video-server system.

## Requirements

### Requirement: Task State Model Must Have Five States
The system MUST define exactly five task states: `queued`, `running`, `succeeded`, `failed`, `canceled`. No independent `expired` state exists.

#### Scenario: State enum contains all required values
- **GIVEN** the `TaskState` enum in `packages/shared/video_downloader_shared/states.py`
- **WHEN** the enum is inspected
- **THEN** it contains exactly: `QUEUED`, `RUNNING`, `SUCCEEDED`, `FAILED`, `CANCELED`
- **AND** the string values are `queued`, `running`, `succeeded`, `failed`, `canceled`

#### Scenario: Expired artifacts do not introduce a new state
- **GIVEN** a task that previously succeeded
- **WHEN** its artifacts expire and are cleaned up
- **THEN** the task state remains `succeeded`
- **AND** the `object_key` is set to `NULL`
- **AND** the `failure_code` is set to `retention_expired`
- **AND** a `task_event` is recorded with message "过期文件已清理，历史记录已保留"

### Requirement: State Transitions Must Follow the Defined State Machine
Only the following transitions are allowed:

| From | To | Trigger |
|------|----|---------|
| `queued` | `running` | Worker picks up the task |
| `queued` | `failed` | Queue unavailable or stale timeout |
| `queued` | `canceled` | User cancels |
| `running` | `succeeded` | Download + probe + upload complete |
| `running` | `failed` | Download, probe, or upload error |
| `running` | `canceled` | User cancels |

#### Scenario: Worker advances task from queued to running
- **GIVEN** a task in `queued` state
- **WHEN** the Worker starts processing
- **THEN** the task state transitions to `running`
- **AND** a `task_event` is recorded

#### Scenario: Successful download transitions to succeeded
- **GIVEN** a task in `running` state
- **WHEN** the Worker completes download, probe, and upload
- **THEN** the task state transitions to `succeeded`
- **AND** the `progress` is set to `100`
- **AND** the `object_key` and `object_size` are populated

#### Scenario: Terminal states cannot transition
- **GIVEN** a task in `succeeded`, `failed`, or `canceled` state
- **WHEN** any state transition is attempted
- **THEN** the transition is rejected

### Requirement: Failure Reasons Must Map to Stable Error Codes
The Worker MUST classify failures using the `WorkerFailureCode` enum. Each code maps to a stable string stored in `task.failure_code`.

#### Scenario: Download failure maps to download_failed
- **GIVEN** the Worker encounters a yt-dlp error
- **WHEN** the failure is classified
- **THEN** the `failure_code` is `download_failed`
- **AND** the `failure_reason` is a user-friendly message with URLs redacted

#### Scenario: Platform rate limit maps to platform_rate_limited
- **GIVEN** the platform returns a rate limit error
- **WHEN** the failure is classified
- **THEN** the `failure_code` is `platform_rate_limited`
- **AND** the task is marked as retryable

#### Scenario: Error codes are stable enum values
- **GIVEN** the `WorkerFailureCode` enum
- **WHEN** any failure classification occurs
- **THEN** the resulting code is one of the enum's defined values
- **AND** no arbitrary strings are used as failure codes

### Requirement: Cancel Must Be Allowed Only for Active Tasks
Only tasks in `queued` or `running` state can be canceled.

#### Scenario: Cancel a queued task
- **GIVEN** a task in `queued` state
- **WHEN** the user requests cancellation
- **THEN** the task state transitions to `canceled`
- **AND** the `failure_reason` is set to "用户已取消任务"
- **AND** the `failure_code` is cleared

#### Scenario: Cancel a succeeded task is rejected
- **GIVEN** a task in `succeeded` state
- **WHEN** the user requests cancellation
- **THEN** the request is rejected with `invalid_state` error code and HTTP 409

### Requirement: Retry Must Create a New Task Linked to the Original
Retrying a failed, canceled, or expired-succeeded task creates a new task with `retry_of_task_id` pointing to the original.

#### Scenario: Retry a failed task
- **GIVEN** a task in `failed` state with `attempt_no = 1`
- **WHEN** the user requests retry
- **THEN** a new task is created with `state = queued`, `attempt_no = 2`, `retry_of_task_id` set to the original task ID
- **AND** the original task is annotated as no longer the latest attempt

#### Scenario: Retry an expired-succeeded task
- **GIVEN** a task in `succeeded` state with `failure_code = "retention_expired"`
- **WHEN** the user requests retry
- **THEN** a new task is created with `state = queued`
- **AND** the original task is annotated as no longer the latest attempt

#### Scenario: Retry a running task is rejected
- **GIVEN** a task in `running` state
- **WHEN** the user requests retry
- **THEN** the request is rejected with `invalid_state` error code and HTTP 409

#### Scenario: Retry a task that already has a retry child is rejected
- **GIVEN** a task that already has a retry child task
- **WHEN** the user requests retry
- **THEN** the request is rejected with `retry_superseded` error code and HTTP 409

### Requirement: API Must Support Task CRUD and Control
The API MUST expose endpoints for task creation, listing, detail, cancellation, retry, event history, and download links.

#### Scenario: Create task returns queued state and task ID
- **GIVEN** an authenticated user submits a valid platform URL
- **WHEN** `POST /api/tasks` is called
- **THEN** the response contains `id`, `state = queued`, and `progress = 0`
- **AND** the task is enqueued for Worker processing

#### Scenario: List tasks returns user's tasks with optional state filter
- **GIVEN** an authenticated user with existing tasks
- **WHEN** `GET /api/tasks?state=succeeded` is called
- **THEN** only tasks in `succeeded` state are returned

#### Scenario: Task detail includes all required fields
- **GIVEN** an existing task
- **WHEN** `GET /api/tasks/{task_id}` is called by the owner
- **THEN** the response includes `id`, `state`, `progress`, `failure_code`, `failure_reason`, `created_at`, `updated_at`

#### Scenario: Download link requires succeeded state with valid object
- **GIVEN** a task in `succeeded` state with a valid `object_key`
- **WHEN** `GET /api/tasks/{task_id}/download-link` is called
- **THEN** a presigned URL with expiration is returned

#### Scenario: Download link rejects expired artifacts
- **GIVEN** a task in `succeeded` state with `object_key = NULL`
- **WHEN** `GET /api/tasks/{task_id}/download-link` is called
- **THEN** the response is HTTP 410 with `retention_expired` error code

### Requirement: Progress Must Follow Defined Semantics
The `progress` field is an integer from 0 to 100.

#### Scenario: Progress starts at 0
- **GIVEN** a newly created task
- **WHEN** the task is in `queued` state
- **THEN** the `progress` is `0`

#### Scenario: Worker sets progress to 5 on start
- **GIVEN** a task in `queued` state
- **WHEN** the Worker starts processing
- **THEN** the `progress` is set to `5`

#### Scenario: Succeeded task has progress 100
- **GIVEN** a task that has completed successfully
- **WHEN** the task is in `succeeded` state
- **THEN** the `progress` is `100`

#### Scenario: Failed task keeps last progress
- **GIVEN** a task in `running` state with `progress = 50`
- **WHEN** the task fails
- **THEN** the `progress` remains `50` (not exceeding 99)

## Error Code Reference

### API Error Codes (AppError)
| Code | HTTP | Meaning |
|------|------|---------|
| `not_found` | 404 | Task not found or not owned by user |
| `invalid_state` | 409 | Operation not allowed in current state |
| `invalid_url` | 422 | URL validation failed |
| `rate_limited` | 429 | Rate limit exceeded |
| `limit_exceeded` | 429 | Quota or concurrency limit exceeded |
| `retention_expired` | 410 | Artifact retention period ended |
| `retry_superseded` | 409 | Task already has a newer retry |
| `queue_unavailable` | 503 | Redis queue is not reachable |

### Worker Failure Codes (WorkerFailureCode)
| Code | Retryable | Meaning |
|------|-----------|---------|
| `download_failed` | Yes | Generic download error |
| `format_unavailable` | No | Requested format not available |
| `file_too_large` | No | File exceeds size limit |
| `media_tools_missing` | No | ffmpeg/ffprobe not available |
| `ffprobe_failed` | No | Media probe error |
| `storage_failed` | Yes | MinIO/S3 upload error |
| `task_timeout` | Yes | Task exceeded max runtime |
| `task_canceled` | No | User-initiated cancellation |
| `platform_restricted` | No | Platform blocks download |
| `platform_rate_limited` | Yes | Platform rate limit |
| `unsupported_platform` | No | Platform not supported |
| `browser_cookies_unavailable` | No | Browser cookie access failed |

## Related Files

- `packages/shared/video_downloader_shared/states.py` — TaskState enum
- `apps/api/app/models.py` — DownloadTask and TaskEvent ORM models
- `apps/api/app/schemas.py` — Pydantic request/response schemas
- `apps/api/app/services/tasks.py` — Task business logic
- `apps/api/app/routers/tasks.py` — API endpoints
- `apps/worker/worker/jobs.py` — Worker orchestration
- `apps/worker/worker/domain.py` — Worker domain types
- `apps/worker/worker/failures.py` — Failure classification
