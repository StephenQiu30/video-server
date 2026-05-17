import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.ai import AIService
from app.services.transcription import TranscriptionService

@pytest.fixture(autouse=True)
def setup_env(monkeypatch):
    from app.core.config import get_settings
    get_settings.cache_clear()
    monkeypatch.setenv("LLM_API_KEY", "fake_key")
    monkeypatch.setenv("TRANSCRIPTION_API_KEY", "fake_key")
    monkeypatch.setenv("LLM_API_BASE_URL", "https://api.deepseek.com/v1")
    monkeypatch.setenv("LLM_MODEL_NAME", "deepseek-chat")
    monkeypatch.setenv("TRANSCRIPTION_API_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.setenv("TRANSCRIPTION_MODEL_NAME", "whisper-large-v3")
    yield
    get_settings.cache_clear()

@pytest.mark.anyio
async def test_ai_summary_generation():
    service = AIService()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Test Summary"}}]
        }
        mock_post.return_value = mock_response
        
        # Test summarize_transcript
        summary = await service.summarize_transcript("Test Transcript")
        assert summary == "Test Summary"
        
@pytest.mark.anyio
async def test_mindmap_generation():
    service = AIService()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "```mermaid\nmindmap\n  root\n```"}}]
        }
        mock_post.return_value = mock_response
        
        mindmap = await service.generate_mindmap("Test Transcript")
        assert "mindmap" in mindmap
        assert "```" not in mindmap

@pytest.mark.anyio
async def test_transcription_failure():
    service = TranscriptionService()
    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Error", request=MagicMock(), response=mock_response
        )
        mock_post.return_value = mock_response
        
        # Test failure
        with patch("os.path.exists", return_value=True):
            with patch("builtins.open", MagicMock()):
                result = await service.transcribe_audio("fake_path.mp3")
                assert result is None
