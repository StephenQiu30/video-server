## MODIFIED Requirements

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
