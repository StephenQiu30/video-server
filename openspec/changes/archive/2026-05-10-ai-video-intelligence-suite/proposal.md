## Why

To provide a competitive edge and match modern video tool standards (inspired by YuPi's downloader), the platform must evolve from a simple downloader into an "Intelligence Suite". AI-powered summaries and mindmaps help users quickly grasp video content without watching the entire video, significantly increasing productivity and platform value.

## What Changes

- **AI Content Summary**: Implement a background pipeline that transcribes video audio and uses LLMs (e.g., DeepSeek) to generate concise summaries.
- **Automated Mind Maps**: Generate structured JSON/Mermaid data from video transcripts to visualize core concepts.
- **Subtitle Extraction**: Automatically extract and store original video subtitles (VTT/SRT) during the download process.
- **Real-time AI Progress**: Update the SSE stream to notify the frontend when AI analysis is in progress or completed.
- **AI Tools API**: New endpoints to trigger analysis manually or fetch AI results.

## Capabilities

### New Capabilities
- `video-ai-intelligence`: High-level content analysis including summaries and mindmaps.
- `video-subtitle-support`: Automated extraction and delivery of video subtitles.

### Modified Capabilities
- `video-download-tasks`: Update task processing to include an optional AI analysis stage.
- `frontend-workbench-ui`: Update to display AI results and manage analysis triggers.

## Impact

- `apps/api`: New database fields for AI results, transcription services, and LLM integration.
- `apps/worker`: New worker jobs for audio extraction, transcription, and summarization.
- `apps/web`: UI integration for displaying summaries, mindmaps, and downloading subtitles.
- `packages/shared`: Updated schemas and task state definitions.
