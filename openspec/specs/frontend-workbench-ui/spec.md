# frontend-workbench-ui Specification

## Purpose
TBD - created by archiving change frontend-redesign-shadcn. Update Purpose after archive.
## Requirements
### Requirement: Advanced Workbench Interaction
The web application SHALL provide an interactive workbench for video download management that follows a clear multi-step flow.

#### Scenario: URL parsing with preview
- **WHEN** a user enters a valid video URL in the workbench
- **THEN** the system fetches and displays a preview including title, cover image, and duration before task creation

#### Scenario: Detailed resolution selection
- **WHEN** a video is parsed successfully
- **THEN** the user SHALL be able to select from available resolutions (e.g., 4K, 1080p, 720p) and formats before starting the download

#### Scenario: Task management list
- **WHEN** a user has active or completed tasks
- **THEN** the workbench SHALL display a list of tasks with real-time progress, status indicators, and actions (Download, Retry, Cancel)
- **AND** the list uses premium components like Progress bars and Badges from Shadcn UI

### Requirement: AI Analysis Placeholders
The workbench SHALL include UI hooks for upcoming AI-powered video analysis features.

#### Scenario: AI feature preview
- **WHEN** a user views a task in the workbench
- **THEN** they see pre-designed "Coming Soon" or "Beta" hooks for: Video Summary, Mind Map, and Comment Analysis
- **AND** these hooks maintain the premium aesthetic of the application

### Requirement: Standalone Task Detail Page
The system SHALL provide a dedicated standalone page `/workbench/task/:id` to display complete details of a selected task, particularly its AI insights and summaries.

#### Scenario: Navigating to standalone page
- **WHEN** the user clicks the "AI 洞察" button on a task in the workbench
- **THEN** the system SHALL navigate the user to `/workbench/task/:id`
- **AND** show a full-page view containing the task title, Markdown content summary, and a visual brain map

