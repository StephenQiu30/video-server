## ADDED Requirements

### Requirement: SSE Real-time Task Status Streaming
The system SHALL use Server-Sent Events (SSE) to push real-time task status updates to the frontend, eliminating the need for periodic HTTP client-side polling.

#### Scenario: Frontend connects to SSE stream
- **WHEN** the authenticated user enters the workbench page
- **THEN** the frontend establishes a persistent connection to the `/api/tasks/stream` endpoint
- **AND** receives immediate real-time tasks updates when any task status changes
