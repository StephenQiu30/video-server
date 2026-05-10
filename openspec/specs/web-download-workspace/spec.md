# web-download-workspace Specification

## Purpose
TBD - created by archiving change regenerate-ant-pro-web-scaffold. Update Purpose after archive.
## Requirements
### Requirement: Ant Design Pro scaffold-based web UI

The web app SHALL use Ant Design Pro scaffold conventions and ProComponents for the local downloader pages instead of custom page shells or custom page width containers.

#### Scenario: Pages use Pro layout containers
- **WHEN** the local user opens `/`, `/workspace`, or `/tasks`
- **THEN** the page content is hosted by ProLayout and PageContainer
- **AND** primary page sizing and spacing are provided by PageContainer, ProCard, ProForm, ProList, or ProTable
- **AND** the app does not use custom root page containers to define main page width

#### Scenario: Downloader flow remains complete
- **WHEN** the web scaffold is regenerated
- **THEN** the user can still parse a URL, choose a resolution preset, create a task, watch progress, open details, retry eligible tasks, cancel running tasks, and download completed files
- **AND** the app does not restore login, SaaS marketing pages, compliance explanation navigation, or left-right workspace layouts

### Requirement: Local download workspace UI

The web app SHALL present the local MVP download workspace as a simple Ant Design Pro blue-white downloader page focused on link input, parsing, task creation, and file download.

#### Scenario: Home page is the downloader
- **WHEN** the local user opens `/`
- **THEN** the page shows the same downloader tool flow as `/workspace`
- **AND** the page does not show a SaaS marketing home page as the primary experience

#### Scenario: Workspace uses single-column downloader layout
- **WHEN** the local user opens `/workspace`
- **THEN** the page shows a centered single-column content flow
- **AND** the main interaction starts with a video URL input and primary parse button
- **AND** the page does not use a left/right split layout for the main workspace content

#### Scenario: Parsed video creates a task
- **WHEN** parsing succeeds for a supported video URL
- **THEN** the page shows title, source URL, duration when available, recommended format, and a create-task action
- **AND** the interaction uses Ant Design or Pro Components instead of custom marketing components

#### Scenario: Successful task is displayed without heavy custom success panel
- **WHEN** a task has succeeded and has downloadable output
- **THEN** the workspace shows filename, size, expiry time, detail action, and download action using Ant Design components
- **AND** the success presentation does not use a large custom green panel

#### Scenario: Compliance page removed from primary navigation
- **WHEN** the local user uses the MVP web application
- **THEN** the primary navigation does not include a dedicated compliance explanation page
- **AND** compliance boundaries remain available through project documentation, user-understandable errors, and smoke checks

