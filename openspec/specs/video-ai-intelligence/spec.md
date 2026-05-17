# Specification: Video AI Intelligence

## Purpose
Provide high-level content analysis for downloaded videos, including automated summaries and visual mindmaps, to enhance user productivity and content discoverability.
## Requirements
### Requirement: AI Content Analysis
The system SHALL provide automated and manual analysis of video content using LLM and transcription services.

#### Scenario 1: Automated AI Analysis after Download
- **GIVEN** a user has "Auto-analyze" enabled in their settings
- **WHEN** a download task for a video completes successfully
- **THEN** the system SHOULD automatically enqueue an AI analysis job
- **AND** the task state SHOULD briefly show "ANALYZING" in the UI
- **AND** once finished, the task SHOULD contain `ai_summary` (Markdown) and `ai_mindmap` (Mermaid)

#### Scenario 2: Manual AI Analysis Trigger
- **GIVEN** a completed task that has NOT been analyzed yet
- **WHEN** the user clicks "Generate AI Summary" in the Workbench
- **THEN** the system SHOULD verify the user's AI quota
- **AND** SHOULD start the analysis process
- **AND** SHOULD update the task results upon completion

#### Scenario 3: AI Analysis Failure Handling
- **GIVEN** an AI analysis job fails (e.g., LLM API error)
- **WHEN** the failure occurs
- **THEN** the task SHOULD remain in `SUCCEEDED` state (download-wise)
- **BUT** SHOULD have an `ai_error` field populated
- **AND** the UI SHOULD show a "Retry AI Analysis" button

### Requirement: PDF Report Generation
The system SHALL support exporting the generated AI content analysis (summary and key metadata) to a professional PDF file using Unicode/Chinese character support.

#### Scenario: PDF report generated successfully
- **WHEN** the user requests a PDF report download for a completed task
- **THEN** the system generates and returns a PDF file containing the task title, source URL, and formatted AI summary

## Infrastructure Support
- The `DownloadTask` model SHALL include the `ai_summary` (Markdown text), `ai_mindmap` (Mermaid text), and `ai_status` fields.
- The AI Service SHALL support audio extraction using `ffmpeg`, transcription via external API (Groq/Whisper), and summarization via DeepSeek.
- The Workbench UI SHALL display a dedicated "AI Results" modal/panel for each task.
- Rendering of Markdown for summaries SHALL be supported on the frontend.
- Rendering of Mind Maps using Mermaid SHALL be supported on the frontend.
