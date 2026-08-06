from __future__ import annotations

import httpx
import pytest
from app.infrastructure.ai import AIProviderErrorCode, OpenAIProviderConfig
from app.infrastructure.ai.error_mapping import provider_error
from openai import APIStatusError, APITimeoutError, RateLimitError


def test_config_is_explicit_and_never_echoes_the_api_key() -> None:
    config = OpenAIProviderConfig(
        api_key="very-secret",
        base_url="https://provider.example/v1",
        analysis_model="analysis",
        transcription_model="whisper-1",
        analysis_schema_version="v1",
        analysis_timeout_seconds=11,
        transcription_timeout_seconds=22,
    )
    assert config.base_url == "https://provider.example/v1"
    assert config.analysis_timeout_seconds == 11
    assert "very-secret" not in repr(config)

    with pytest.raises(ValueError) as captured:
        OpenAIProviderConfig(
            api_key="very-secret",
            base_url="ftp://provider.example",
            analysis_model="analysis",
            transcription_model="whisper-1",
            analysis_schema_version="v1",
        )
    assert "very-secret" not in str(captured.value)


def test_provider_error_classification_is_stable_and_redacted() -> None:
    request = httpx.Request("POST", "https://provider.example/v1/responses")

    def status_error(status: int, *, rate_limit: bool = False) -> APIStatusError:
        response = httpx.Response(status, request=request)
        if rate_limit:
            return RateLimitError("sensitive body", response=response, body={})
        return APIStatusError("sensitive body", response=response, body={})

    cases = (
        (status_error(429, rate_limit=True), AIProviderErrorCode.RATE_LIMITED),
        (status_error(503), AIProviderErrorCode.UNAVAILABLE),
        (APITimeoutError(request), AIProviderErrorCode.TIMEOUT),
        (ValueError("bad payload"), AIProviderErrorCode.INVALID_RESPONSE),
    )
    for error, expected in cases:
        mapped = provider_error(error)
        assert mapped.code is expected
        assert str(mapped) == expected.value
        assert "sensitive" not in str(mapped)
