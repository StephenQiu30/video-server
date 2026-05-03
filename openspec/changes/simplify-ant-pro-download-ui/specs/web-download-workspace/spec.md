## ADDED Requirements

### Requirement: Local download workspace UI

The web app SHALL present the local MVP download workspace as a simple Ant Design Pro blue-white downloader page focused on link input, parsing, task creation, and file download.

#### Scenario: Workspace uses single-column downloader layout
- **WHEN** the local user opens `/workspace`
- **THEN** the page shows a centered single-column content flow
- **AND** the main interaction starts with a video URL input and primary parse button
- **AND** the page does not use a left/right split layout for the main workspace content

#### Scenario: Successful task is displayed without heavy custom success panel
- **WHEN** a task has succeeded and has downloadable output
- **THEN** the workspace shows filename, size, expiry time, detail action, and download action using Ant Design components
- **AND** the success presentation does not use a large custom green panel

#### Scenario: Compliance page is single-column
- **WHEN** the local user opens `/compliance`
- **THEN** allowed and denied boundaries are shown in a vertical single-column flow
- **AND** the page does not use a left/right split layout for those boundary sections
