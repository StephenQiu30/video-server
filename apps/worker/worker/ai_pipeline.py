import asyncio
import subprocess

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.models import DownloadTask
from app.services.tasks import add_task_event
from video_downloader_shared.states import TaskState
from worker.domain import AIProcessResult, AIProcessStatus, DownloadArtifact


def process_ai_pipeline(db: Session, task: DownloadTask, artifact: DownloadArtifact) -> AIProcessResult:
    settings = get_settings()
    if not settings.llm_api_key or not settings.transcription_api_key:
        task.ai_status = AIProcessStatus.SKIPPED.value
        db.commit()
        return AIProcessResult(status=AIProcessStatus.SKIPPED)

    task.ai_status = AIProcessStatus.PROCESSING.value
    db.commit()

    audio_path = artifact.path.with_suffix(".mp3")
    try:
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-i",
                str(artifact.path),
                "-vn",
                "-ar",
                "16000",
                "-ac",
                "1",
                "-b:a",
                "64k",
                str(audio_path),
            ],
            check=True,
            capture_output=True,
        )

        from app.services.ai import AIService
        from app.services.transcription import TranscriptionService

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            transcript = loop.run_until_complete(TranscriptionService().transcribe_audio(str(audio_path)))
            if not transcript:
                raise RuntimeError("音频转录失败")
            summary = loop.run_until_complete(AIService().summarize_transcript(transcript))
            mindmap = loop.run_until_complete(AIService().generate_mindmap(transcript))
        finally:
            loop.close()

        task.ai_summary = summary
        task.ai_mindmap = mindmap
        task.ai_status = AIProcessStatus.COMPLETED.value
        task.ai_error = None
        add_task_event(db, task, TaskState.SUCCEEDED, "AI 智能分析完成")
        db.commit()
        return AIProcessResult(status=AIProcessStatus.COMPLETED, summary=summary, mindmap=mindmap)
    except Exception as exc:
        task.ai_status = AIProcessStatus.FAILED.value
        task.ai_error = str(exc)
        add_task_event(db, task, TaskState.SUCCEEDED, f"AI 智能分析失败: {str(exc)}")
        db.commit()
        return AIProcessResult(status=AIProcessStatus.FAILED, error=str(exc))
    finally:
        if audio_path.exists():
            audio_path.unlink()
