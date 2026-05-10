import logging
import os
from typing import Optional

import httpx
from app.core.config import get_settings

logger = logging.getLogger(__name__)

class TranscriptionService:
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.transcription_api_key
        # Default to Groq for speed/cost, can be OpenAI
        self.base_url = settings.transcription_api_base_url or "https://api.groq.com/openai/v1"
        self.model = settings.transcription_model_name or "whisper-large-v3"

    async def transcribe_audio(self, audio_file_path: str) -> Optional[str]:
        if not self.api_key:
            logger.warning("Transcription API key not configured, skipping")
            return None

        if not os.path.exists(audio_file_path):
            logger.error(f"Audio file not found: {audio_file_path}")
            return None

        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                with open(audio_file_path, "rb") as audio_file:
                    files = {"file": (os.path.basename(audio_file_path), audio_file, "audio/mpeg")}
                    data = {"model": self.model, "response_format": "text"}
                    
                    response = await client.post(
                        f"{self.base_url}/audio/transcriptions",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                        files=files,
                        data=data
                    )
                    response.raise_for_status()
                    return response.text
        except Exception as e:
            logger.error(f"Error during transcription: {str(e)}")
            return None
