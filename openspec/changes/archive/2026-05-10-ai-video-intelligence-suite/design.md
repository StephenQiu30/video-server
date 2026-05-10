## Context

Currently, the system provides raw video downloads. To implement YuPi-inspired "Universal Downloader + AI Intelligence", we need a reliable pipeline for transcription and summarization. This involves post-processing downloaded files to extract insights.

## Goals / Non-Goals

**Goals:**
- **Asynchronous Processing**: AI analysis runs as a separate background job after the video is successfully downloaded and stored.
- **Accurate Summaries**: Use high-quality LLMs (DeepSeek-V3/R1) for content summarization.
- **Visual Mind Maps**: Generate structured data compatible with frontend mind-mapping libraries (e.g., React Flow or Mermaid).
- **Subtitle Availability**: Ensure subtitles are extracted during `yt-dlp` download and made available to the user.

**Non-Goals:**
- **Real-time Video Overlay**: No burning of subtitles or summaries into the video file itself.
- **Self-hosted LLMs**: We will use API-based providers to maintain a lightweight infrastructure.

## Decisions

- **Transcription**: Use **Groq (Whisper-large-v3)** or **OpenAI Whisper API** for ultra-fast, high-accuracy transcription of extracted audio.
- **Summarization**: Use **DeepSeek** (via API) for reasoning-heavy summarization and mindmap data generation.
- **Audio Extraction**: Use `ffmpeg` within the existing worker to extract a lightweight audio track (e.g., 64kbps MP3) for transcription, reducing bandwidth and cost.
- **Storage**: Store JSON summaries and mindmap structures in the `DownloadTask` record (PostgreSQL) and transcripts in Object Storage (MinIO/S3).
- **Trigger**: AI analysis can be triggered automatically (based on user settings) or manually via the Workbench UI.

## Risks / Trade-offs

- **[Risk] High Cost of API Calls**: Frequent AI analysis can be expensive.
  - **[Mitigation]**: Implement AI quotas per user and allow users to choose which videos to analyze.
- **[Risk] Transcription Privacy**: Sending audio to 3rd party APIs.
  - **[Mitigation]**: Disclose this in the Privacy Notice and allow users to opt-out.
- **[Risk] Worker Load**: Extraction and upload of audio adds load to workers.
  - **[Mitigation]**: Process AI jobs in a separate low-priority queue.
