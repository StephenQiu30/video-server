## MODIFIED Requirements

### Requirement: PDF Report Generation
The system SHALL support exporting the generated AI content analysis (summary and key metadata) to a professional PDF file using Unicode/Chinese character support, both from the workspace and from the standalone detail page.

#### Scenario: PDF report exported from detail page
- **WHEN** the user requests a PDF report download from the standalone task detail page
- **THEN** the system generates and returns a PDF file containing the task title, source URL, and formatted AI summary
