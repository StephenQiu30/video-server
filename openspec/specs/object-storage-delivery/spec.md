# object-storage-delivery Specification

## Purpose
TBD - created by archiving change bootstrap-mvp-foundation. Update Purpose after archive.
## Requirements
### Requirement: Private object storage bucket
The system SHALL store downloaded files in a private MinIO / S3 compatible bucket.

#### Scenario: File stored privately
- **WHEN** a download task succeeds
- **THEN** the output file is stored in a private object storage bucket and is not publicly readable by default

### Requirement: User and task scoped object keys
The system SHALL store objects using keys scoped by user and task identifiers.

#### Scenario: Object key generated
- **WHEN** a task output is stored
- **THEN** the object key follows the pattern `users/{user_id}/tasks/{task_id}/{filename}`

### Requirement: Presigned download URL
The system SHALL provide file downloads through short-lived backend-generated URLs without exposing object storage internal endpoints to the frontend.

#### Scenario: Download URL requested
- **WHEN** a local MVP user requests a download link for a succeeded task with a retained object
- **THEN** the system returns a backend API download URL with a default TTL of 15 minutes
- **AND** the returned URL does not expose MinIO / S3 internal service hosts or access keys

#### Scenario: Signed proxy download
- **WHEN** the user opens a valid backend signed download URL before it expires
- **THEN** the API streams the retained object from private storage with an attachment disposition

#### Scenario: Invalid or expired signed download
- **WHEN** the download signature is invalid or the signed URL has expired
- **THEN** the API rejects the request without returning object bytes

#### Scenario: Retention expired
- **WHEN** the task output retention has expired or the object has been cleaned
- **THEN** the API no longer returns a valid download URL or file stream

### Requirement: File retention cleanup
The system SHALL clean up task output files after the configured retention period.

#### Scenario: Retention expired
- **WHEN** a task output exceeds the default 24 hour retention period
- **THEN** the system removes or marks the object for removal and no longer returns a valid download URL

