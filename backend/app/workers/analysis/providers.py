from __future__ import annotations

from app.core.config import Settings
from app.infrastructure.ai import AnalysisModelConfig, TranscriptionConfig


def transcription_config(settings: Settings) -> TranscriptionConfig:
    if settings.openai_api_key is None:
        raise ValueError("OPENAI_API_KEY is required for audio transcription")
    return TranscriptionConfig(
        api_key=settings.openai_api_key.get_secret_value(),
        base_url=settings.openai_base_url,
        model=settings.openai_transcription_model,
        timeout_seconds=settings.transcription_timeout_seconds,
    )


def analysis_model_config(settings: Settings) -> AnalysisModelConfig:
    if settings.analysis_provider == "deepseek":
        key = (
            None
            if settings.deepseek_api_key is None
            else settings.deepseek_api_key.get_secret_value()
        )
        return AnalysisModelConfig(
            provider="deepseek",
            model=settings.deepseek_analysis_model,
            schema_version=settings.analysis_schema_version,
            base_url=settings.deepseek_base_url,
            api_key=key,
            timeout_seconds=settings.analysis_timeout_seconds,
            max_output_tokens=settings.analysis_max_output_tokens,
        )
    return AnalysisModelConfig(
        provider="ollama",
        model=settings.ollama_analysis_model,
        schema_version=settings.analysis_schema_version,
        base_url=settings.ollama_base_url,
        timeout_seconds=settings.analysis_timeout_seconds,
        max_output_tokens=settings.analysis_max_output_tokens,
    )
