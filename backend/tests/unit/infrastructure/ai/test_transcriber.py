from __future__ import annotations

from types import SimpleNamespace

import pytest
from app.application.analysis import AudioChunk
from app.infrastructure.ai import OpenAITranscriber, ProviderInvalidResponse
from tests.unit.infrastructure.ai.fakes import fake_client, provider_config


def _verbose(*segments: tuple[float, float, str], language: str = "en") -> object:
    return SimpleNamespace(
        language=language,
        segments=[
            SimpleNamespace(start=start, end=end, text=text)
            for start, end, text in segments
        ],
    )


@pytest.mark.asyncio
async def test_whisper_uses_segment_timestamps_and_absolute_chunk_offsets() -> None:
    client, _, calls = fake_client(
        transcription_outcomes=[
            _verbose((0.0, 0.8, "first"), (0.75, 2.0, "second")),
            _verbose((0.0, 1.0, "third"), language="fr"),
        ]
    )
    chunks = (
        AudioChunk(9, 12_000, 13_000, b"wav-2"),
        AudioChunk(4, 10_000, 12_000, b"wav-1"),
    )

    result = await OpenAITranscriber(provider_config(), client=client).transcribe(
        chunks, "en"
    )

    assert [segment.id for segment in result.segments] == [
        "segment-000004-000000",
        "segment-000004-000001",
        "segment-000009-000000",
    ]
    assert [(item.start_ms, item.end_ms) for item in result.segments] == [
        (10_000, 10_800),
        (10_800, 12_000),
        (12_000, 13_000),
    ]
    assert calls.calls[0]["response_format"] == "verbose_json"
    assert calls.calls[0]["timestamp_granularities"] == ["segment"]
    assert calls.calls[0]["file"][0] == "chunk-000004.wav"


@pytest.mark.asyncio
async def test_non_whisper_uses_each_audio_chunks_absolute_boundaries() -> None:
    client, _, calls = fake_client(
        transcription_outcomes=[
            SimpleNamespace(text="one"),
            SimpleNamespace(text="two", language="de"),
        ]
    )
    config = provider_config(transcription_model="gpt-4o-mini-transcribe")
    chunks = (
        AudioChunk(1, 0, 500, b"a"),
        AudioChunk(2, 500, 1_500, b"b"),
    )

    result = await OpenAITranscriber(config, client=client).transcribe(chunks, None)

    assert [(item.id, item.start_ms, item.end_ms) for item in result.segments] == [
        ("segment-000001-000000", 0, 500),
        ("segment-000002-000000", 500, 1_500),
    ]
    assert [item.language for item in result.segments] == ["und", "de"]
    assert all("timestamp_granularities" not in call for call in calls.calls)


@pytest.mark.asyncio
async def test_transcriber_rejects_invalid_input_or_provider_timestamps() -> None:
    client, _, calls = fake_client()
    with pytest.raises(ValueError, match="audio chunks"):
        await OpenAITranscriber(
            provider_config(max_audio_bytes=2), client=client
        ).transcribe((AudioChunk(1, 0, 1_000, b"too-large"),), None)
    assert not calls.calls

    invalid_client, _, _ = fake_client(
        transcription_outcomes=[_verbose((0.0, 2.0, "outside"))]
    )
    with pytest.raises(ProviderInvalidResponse):
        await OpenAITranscriber(provider_config(), client=invalid_client).transcribe(
            (AudioChunk(1, 0, 1_000, b"wav"),), None
        )
