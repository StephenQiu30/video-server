# Design: Video Processing & AI Intelligence Suite

## Backend Architecture

### PDF Generation Service
- **Service**: `app/services/pdf.py`
- **Library**: `fpdf2` (support for Unicode/Chinese characters is critical).
- **Functionality**: `generate_task_report(task: DownloadTask) -> bytes`.
- **Content**: Task title, source URL, AI summary (parsed from Markdown to plain text/simple PDF styling).

### SSE Streaming
- **Endpoint**: `/api/tasks/stream` (already exists, but needs to ensure it's used effectively).
- **Mechanism**: The frontend will establish a persistent connection. The backend yields the user's task list whenever a change is detected (simplified via 1s polling in the generator).

### API Endpoints
- `GET /api/tasks/{id}/pdf`: Returns a PDF file of the intelligence report.
- `GET /api/tasks/{id}/download-link`: (Exists) Provides a signed URL for the video file.

## Frontend Architecture

### SSE Hook
- Create a custom hook `useTaskStream` that manages the `EventSource`.
- Updates the local state and triggers `queryClient` invalidation or manual state update.

### UI Components
- **DownloadButton**: A Shadcn button in the task list.
- **ExportButton**: In the AI Insight modal, triggers a browser download for the PDF.

## Data Flow
1. User submits URL.
2. Worker downloads video -> Uploads to S3.
3. Worker extracts audio -> Transcribes -> AI Summarizes -> AI Mindmaps -> Updates DB.
4. Frontend SSE receives updates in real-time.
5. User clicks "AI Insight" -> Views Report.
6. User clicks "Download" or "Export PDF".
