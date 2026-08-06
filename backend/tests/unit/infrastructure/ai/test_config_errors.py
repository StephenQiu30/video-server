from __future__ import annotations

import httpx
import pytest
from app.infrastructure.ai import (
    AIProviderErrorCode,
    AnalysisModelConfig,
    TranscriptionConfig,
)
from app.infrastructure.ai.error_mapping import provider_error
from app.infrastructure.ai.models import create_analysis_model
from ollama import ResponseError
from openai import APIStatusError, APITimeoutError, RateLimitError


def test_provider_configs_are_explicit_and_never_echo_secrets() -> None:
    transcription = TranscriptionConfig(
        api_key="transcription-secret",
        base_url="https://provider.example/v1",
        model="whisper-1",
        timeout_seconds=22,
    )
    deepseek = AnalysisModelConfig(
        provider="deepseek",
        api_key="deepseek-secret",
        base_url="https://api.deepseek.com",
        model="deepseek-v4-flash",
        schema_version="analysis.v1",
        timeout_seconds=11,
    )

    assert transcription.timeout_seconds == 22
    assert deepseek.model == "deepseek-v4-flash"
    assert "transcription-secret" not in repr(transcription)
    assert "deepseek-secret" not in repr(deepseek)

    with pytest.raises(ValueError, match="DEEPSEEK_API_KEY"):
        AnalysisModelConfig(
            provider="deepseek",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            schema_version="analysis.v1",
        )
    with pytest.raises(ValueError, match="HTTP"):
        AnalysisModelConfig(
            provider="ollama",
            base_url="ftp://provider.example",
            model="deepseek-r1:8b",
            schema_version="analysis.v1",
        )


def test_langchain_models_are_built_for_deepseek_and_ollama() -> None:
    deepseek = create_analysis_model(
        AnalysisModelConfig(
            provider="deepseek",
            api_key="deepseek-secret",
            base_url="https://api.deepseek.com",
            model="deepseek-v4-flash",
            schema_version="analysis.v1",
        )
    )
    ollama = create_analysis_model(
        AnalysisModelConfig(
            provider="ollama",
            base_url="http://localhost:11434",
            model="deepseek-r1:8b",
            schema_version="analysis.v1",
        )
    )

    assert callable(deepseek.ainvoke)
    assert callable(ollama.ainvoke)


def test_provider_error_classification_is_stable_and_redacted() -> None:
    request = httpx.Request("POST", "https://provider.example/v1/chat")

    def status_error(status: int, *, rate_limit: bool = False) -> APIStatusError:
        response = httpx.Response(status, request=request)
        if rate_limit:
            return RateLimitError("sensitive body", response=response, body={})
        return APIStatusError("sensitive body", response=response, body={})

    cases = (
        (status_error(429, rate_limit=True), AIProviderErrorCode.RATE_LIMITED),
        (status_error(503), AIProviderErrorCode.UNAVAILABLE),
        (APITimeoutError(request), AIProviderErrorCode.TIMEOUT),
        (ResponseError("sensitive body", 404), AIProviderErrorCode.REJECTED),
        (ValueError("bad payload"), AIProviderErrorCode.INVALID_RESPONSE),
    )
    for error, expected in cases:
        mapped = provider_error(error)
        assert mapped.code is expected
        assert str(mapped) == expected.value
        assert "sensitive" not in str(mapped)
