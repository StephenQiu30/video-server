# web-download-workspace Specification

## Purpose
TBD - created by archiving change regenerate-ant-pro-web-scaffold. Update Purpose after archive.
## Requirements
### Requirement: Ant Design Pro scaffold-based web UI
The web application SHALL migrate away from Ant Design Pro and use a custom Vite-based React architecture with Shadcn UI and Tailwind CSS.

#### Scenario: Pages use modern UI components
- **WHEN** a user navigates through the application
- **THEN** the layout is managed by custom Shadcn-based Shell and Page components
- **AND** the app no longer depends on ProLayout or PageContainer

### Requirement: Local download workspace UI
The web application SHALL provide a premium, unified workspace for task management.

#### Scenario: Home page transitions based on auth
- **WHEN** a guest user visits `/`
- **THEN** they see the landing page
- **WHEN** an authenticated user visits `/` or `/workbench`
- **THEN** they see the interactive workbench

### Requirement: SSE Real-time Task Status Streaming
The system SHALL use Server-Sent Events (SSE) to push real-time task status updates to the frontend, eliminating the need for periodic HTTP client-side polling.

#### Scenario: Frontend connects to SSE stream
- **WHEN** the authenticated user enters the workbench page
- **THEN** the frontend establishes a persistent connection to the `/api/tasks/stream` endpoint
- **AND** receives immediate real-time tasks updates when any task status changes

