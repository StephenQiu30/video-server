from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from urllib.parse import urlsplit

from openai import AsyncOpenAI

OPENAI_MAX_AUDIO_BYTES = 25_000_000


@dataclass(frozen=True, slots=True)
class OpenAIProviderConfig:
    api_key: str = field(repr=False)
    analysis_model: str
    transcription_model: str
    analysis_schema_version: str
    base_url: str | None = None
    analysis_timeout_seconds: float = 120.0
    transcription_timeout_seconds: float = 120.0
    max_audio_bytes: int = OPENAI_MAX_AUDIO_BYTES

    def __post_init__(self) -> None:
        _required(self.api_key, "api_key")
        _required(self.analysis_model, "analysis_model")
        _required(self.transcription_model, "transcription_model")
        _required(self.analysis_schema_version, "analysis_schema_version")
        _positive_timeout(self.analysis_timeout_seconds, "analysis timeout")
        _positive_timeout(self.transcription_timeout_seconds, "transcription timeout")
        if not 0 < self.max_audio_bytes <= OPENAI_MAX_AUDIO_BYTES:
            raise ValueError("max audio bytes must be within the provider limit")
        if self.base_url is not None:
            _validate_base_url(self.base_url)


def create_openai_client(config: OpenAIProviderConfig) -> AsyncOpenAI:
    if config.base_url is None:
        return AsyncOpenAI(
            api_key=config.api_key,
            timeout=max(
                config.analysis_timeout_seconds,
                config.transcription_timeout_seconds,
            ),
            max_retries=0,
        )
    return AsyncOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=max(
            config.analysis_timeout_seconds,
            config.transcription_timeout_seconds,
        ),
        max_retries=0,
    )


def _required(value: str, field: str) -> None:
    if not value or value != value.strip():
        raise ValueError(f"{field} must be a non-empty normalized string")


def _positive_timeout(value: float, field: str) -> None:
    if isinstance(value, bool) or not isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be a positive finite number")


def _validate_base_url(value: str) -> None:
    if value != value.strip():
        raise ValueError("base_url must be normalized")
    parsed = urlsplit(value)
    if (
        parsed.scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise ValueError("base_url must be an HTTP(S) URL without credentials")
