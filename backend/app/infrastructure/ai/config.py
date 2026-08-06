from __future__ import annotations

from dataclasses import dataclass, field
from math import isfinite
from typing import Literal
from urllib.parse import urlsplit

from openai import AsyncOpenAI

OPENAI_MAX_AUDIO_BYTES = 25_000_000
AnalysisProvider = Literal["deepseek", "ollama"]


@dataclass(frozen=True, slots=True)
class TranscriptionConfig:
    api_key: str = field(repr=False)
    model: str
    base_url: str | None = None
    timeout_seconds: float = 300.0
    max_audio_bytes: int = OPENAI_MAX_AUDIO_BYTES

    def __post_init__(self) -> None:
        _required(self.api_key, "api_key")
        _required(self.model, "transcription_model")
        _positive_timeout(self.timeout_seconds, "transcription timeout")
        if not 0 < self.max_audio_bytes <= OPENAI_MAX_AUDIO_BYTES:
            raise ValueError("max audio bytes must be within the provider limit")
        if self.base_url is not None:
            _validate_base_url(self.base_url)


@dataclass(frozen=True, slots=True)
class AnalysisModelConfig:
    provider: AnalysisProvider
    model: str
    schema_version: str
    base_url: str
    api_key: str | None = field(default=None, repr=False)
    timeout_seconds: float = 120.0
    max_output_tokens: int = 16_384

    def __post_init__(self) -> None:
        if self.provider not in {"deepseek", "ollama"}:
            raise ValueError("analysis provider must be deepseek or ollama")
        _required(self.model, "analysis_model")
        _required(self.schema_version, "analysis_schema_version")
        _validate_base_url(self.base_url)
        _positive_timeout(self.timeout_seconds, "analysis timeout")
        if isinstance(self.max_output_tokens, bool) or not (
            1_024 <= self.max_output_tokens <= 131_072
        ):
            raise ValueError("max output tokens must be between 1024 and 131072")
        if self.provider == "deepseek":
            if self.api_key is None:
                raise ValueError("DEEPSEEK_API_KEY is required for DeepSeek")
            _required(self.api_key, "deepseek_api_key")


def create_transcription_client(config: TranscriptionConfig) -> AsyncOpenAI:
    if config.base_url is None:
        return AsyncOpenAI(
            api_key=config.api_key,
            timeout=config.timeout_seconds,
            max_retries=0,
        )
    return AsyncOpenAI(
        api_key=config.api_key,
        base_url=config.base_url,
        timeout=config.timeout_seconds,
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
