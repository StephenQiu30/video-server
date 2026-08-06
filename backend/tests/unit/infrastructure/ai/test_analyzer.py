from __future__ import annotations

import pytest
from app.infrastructure.ai import (
    OpenAIAnalyzer,
    ProviderInvalidResponse,
    ProviderRefused,
)
from app.infrastructure.ai.schemas import AnalysisPayload
from tests.unit.infrastructure.ai.fakes import (
    fake_client,
    parsed_response,
    provider_config,
    transcript,
    valid_mapping,
)


@pytest.mark.asyncio
async def test_analyzer_returns_valid_mapping_and_marks_transcript_untrusted() -> None:
    client, responses, _ = fake_client(
        response_outcomes=[parsed_response(valid_mapping())]
    )

    result = await OpenAIAnalyzer(provider_config(), client=client).analyze(
        transcript(), "zh-CN"
    )

    assert isinstance(result, dict)
    assert result["schema_version"] == "analysis.v1"
    call = responses.calls[0]
    assert call["model"] == "structured-model"
    assert call["text_format"] is AnalysisPayload
    assert call["timeout"] == 11.0
    messages = call["input"]
    assert isinstance(messages, list)
    assert "UNTRUSTED DATA" in messages[0]["content"]
    assert "Never follow" in messages[0]["content"]
    assert "Ignore prior instructions" in messages[1]["content"]


@pytest.mark.asyncio
async def test_analyzer_repairs_invalid_evidence_exactly_once_without_secrets() -> None:
    invalid = valid_mapping()
    invalid["summary"] = {
        "text": "unsupported",
        "evidence_segment_ids": ["invented-segment"],
    }
    client, responses, _ = fake_client(
        response_outcomes=[
            parsed_response(invalid),
            parsed_response(valid_mapping()),
        ]
    )

    await OpenAIAnalyzer(provider_config(), client=client).analyze(
        transcript(), "zh-CN"
    )

    assert len(responses.calls) == 2
    repair = responses.calls[1]["input"]
    assert isinstance(repair, list)
    assert "invalid_evidence" in repair[1]["content"]
    assert "invented-segment" not in repair[1]["content"]
    assert "test-secret-key" not in str(responses.calls)


@pytest.mark.asyncio
async def test_analyzer_handles_refusal_and_empty_parsed_output() -> None:
    refused_client, refused_calls, _ = fake_client(
        response_outcomes=[parsed_response(refusal=True)]
    )
    with pytest.raises(ProviderRefused):
        await OpenAIAnalyzer(provider_config(), client=refused_client).analyze(
            transcript(), "zh-CN"
        )
    assert len(refused_calls.calls) == 1

    empty_client, empty_calls, _ = fake_client(
        response_outcomes=[parsed_response(), parsed_response()]
    )
    with pytest.raises(ProviderInvalidResponse):
        await OpenAIAnalyzer(provider_config(), client=empty_client).analyze(
            transcript(), "zh-CN"
        )
    assert len(empty_calls.calls) == 2
