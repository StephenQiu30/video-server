## ADDED Requirements

### Requirement: Standalone Task Detail Page
The system SHALL provide a dedicated standalone page `/workbench/task/:id` to display complete details of a selected task, particularly its AI insights and summaries.

#### Scenario: Navigating to standalone page
- **WHEN** the user clicks the "AI 洞察" button on a task in the workbench
- **THEN** the system SHALL navigate the user to `/workbench/task/:id`
- **AND** show a full-page view containing the task title, Markdown content summary, and a visual brain map
