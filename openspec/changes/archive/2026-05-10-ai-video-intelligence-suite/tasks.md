## 1. Backend Infrastructure

- [x] 1.1 Add AI-related fields to `DownloadTask` model in `apps/api/app/models.py`.
- [x] 1.2 Generate and apply database migration for new fields.
- [x] 1.3 Update `TaskRead` and `TaskCreate` schemas in `apps/api/app/schemas.py`.

## 2. AI Intelligence Services

- [x] 2.1 Create `apps/api/app/services/ai.py` for LLM (DeepSeek) integration.
- [x] 2.2 Create `apps/api/app/services/transcription.py` for Whisper/Groq integration.
- [x] 2.3 Add audio extraction logic to worker utilities using `ffmpeg`.

## 3. Worker Integration

- [x] 3.1 Implement `analyze_video_task` in `apps/worker/worker.py`.
- [x] 3.2 Update the main download success handler to trigger AI analysis if requested.
- [x] 3.3 Ensure subtitles are extracted and stored during the `yt-dlp` download stage.

## 4. Frontend Workbench Enhancement

- [x] 4.1 Implement `AISummary` component with Markdown rendering support.
- [x] 4.2 Implement `MindMap` component (using Mermaid or similar) in the workbench.
- [x] 4.3 Add "Analysis" tab and "Regenerate AI Analysis" button to task detail view.
- [x] 4.4 Update SSE logic to handle AI status updates in real-time.

## 5. Verification and Cleanup

- [x] 5.1 Add `pytest` tests for AI service mocking and pipeline flow.
- [x] 5.2 Perform manual end-to-end verification.
- [x] 5.3 Archive the change and update specifications.
