# Specification: Video AI Intelligence

## Capabilities
- `video-ai-intelligence`: High-level content analysis including summaries and mindmaps.

## Scenarios

### Scenario 1: Automated AI Analysis after Download
**Given** a user has "Auto-analyze" enabled in their settings
**When** a download task for a video (e.g., "AI Revolution") completes successfully
**Then** the system SHOULD automatically enqueue an AI analysis job
**And** the task state SHOULD briefly show "ANALYZING" in the UI
**And** once finished, the task SHOULD contain `ai_summary` (Markdown) and `ai_mindmap` (JSON/Mermaid)

### Scenario 2: Manual AI Analysis Trigger
**Given** a completed task that has NOT been analyzed yet
**When** the user clicks "Generate AI Summary" in the Workbench
**Then** the system SHOULD verify the user's AI quota
**And** SHOULD start the analysis process
**And** SHOULD update the task results upon completion

### Scenario 3: AI Analysis Failure Handling
**Given** an AI analysis job fails (e.g., LLM API error)
**When** the failure occurs
**Then** the task SHOULD remain in `SUCCEEDED` state (download-wise)
**But** SHOULD have an `ai_error` field populated
**And** the UI SHOULD show a "Retry AI Analysis" button

## Requirements

### Backend
- `DownloadTask` model must include:
    - `ai_summary`: text (Markdown)
    - `ai_mindmap`: json
    - `ai_transcript_key`: string (pointer to object storage)
    - `ai_status`: enum (pending, processing, completed, failed)
- AI Service must support:
    - Audio extraction using `ffmpeg`.
    - Transcription via External API.
    - Summarization via DeepSeek.

### Frontend
- Workbench UI must display a dedicated "AI Results" tab/panel for each task.
- Support for rendering Markdown (for summaries).
- Support for rendering Mind Maps (using a library like `react-flow` or `mermaid`).
