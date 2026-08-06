from __future__ import annotations

from copy import deepcopy

import pytest
from app.infrastructure.ai import LangChainAnalyzer, ProviderInvalidResponse
from app.infrastructure.ai.schemas import AnalysisPayload
from langchain_core.messages import HumanMessage, SystemMessage
from tests.unit.infrastructure.ai.fakes import (
    FakeStructuredModel,
    analysis_config,
    transcript,
    valid_mapping,
    valid_payload,
)


@pytest.mark.asyncio
async def test_analyzer_returns_valid_mapping_and_marks_transcript_untrusted() -> None:
    model = FakeStructuredModel([valid_payload()])

    result = await LangChainAnalyzer(analysis_config(), model=model).analyze(
        transcript(), "zh-CN"
    )

    assert isinstance(result, dict)
    assert result["schema_version"] == "analysis.v1"
    messages = model.calls[0]
    assert isinstance(messages, list)
    assert isinstance(messages[0], SystemMessage)
    assert "UNTRUSTED DATA" in str(messages[0].content)
    assert "valid JSON" in str(messages[0].content)
    assert isinstance(messages[1], HumanMessage)
    assert "Ignore prior instructions" in str(messages[1].content)
    assert "output_json_schema" in str(messages[1].content)


@pytest.mark.asyncio
async def test_analyzer_repairs_invalid_evidence_exactly_once_without_secrets() -> None:
    invalid = deepcopy(valid_mapping())
    invalid["summary"] = {
        "text": "unsupported",
        "evidence_segment_ids": ["invented-segment"],
    }
    model = FakeStructuredModel(
        [AnalysisPayload.model_validate(invalid), valid_payload()]
    )

    await LangChainAnalyzer(analysis_config(), model=model).analyze(
        transcript(), "zh-CN"
    )

    assert len(model.calls) == 2
    repair = model.calls[1]
    assert isinstance(repair, list)
    assert "invalid_evidence" in str(repair[1].content)
    assert "invented-segment" not in str(repair[1].content)
    assert "test-secret-key" not in str(model.calls)


@pytest.mark.asyncio
async def test_analyzer_rejects_invalid_structured_output_after_one_repair() -> None:
    model = FakeStructuredModel([None, None])

    with pytest.raises(ProviderInvalidResponse):
        await LangChainAnalyzer(analysis_config(), model=model).analyze(
            transcript(), "zh-CN"
        )

    assert len(model.calls) == 2
