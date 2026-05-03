## ADDED Requirements

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
