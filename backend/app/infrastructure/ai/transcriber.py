from __future__ import annotations

from math import isfinite

from openai import AsyncOpenAI, OpenAIError
from pydantic import ValidationError

from app.application.analysis import AudioChunk
from app.domain.analysis import Transcript, TranscriptSegment
from app.infrastructure.ai.config import OpenAIProviderConfig, create_openai_client
from app.infrastructure.ai.error_mapping import provider_error
from app.infrastructure.ai.errors import ProviderInvalidResponse


class OpenAITranscriber:
    def __init__(
        self,
        config: OpenAIProviderConfig,
        *,
        client: AsyncOpenAI | None = None,
    ) -> None:
        self._config = config
        self._client = client or create_openai_client(config)

    async def transcribe(
        self, chunks: tuple[AudioChunk, ...], language_hint: str | None
    ) -> Transcript:
        ordered = _validated_chunks(chunks, self._config.max_audio_bytes)
        segments: list[TranscriptSegment] = []
        for chunk in ordered:
            response = await self._transcribe_chunk(chunk, language_hint)
            if self._config.transcription_model == "whisper-1":
                segments.extend(_whisper_segments(response, chunk, segments))
            else:
                segments.append(_chunk_segment(response, chunk, language_hint))
        if not segments:
            raise ProviderInvalidResponse()
        return Transcript(tuple(segments))

    async def _transcribe_chunk(
        self, chunk: AudioChunk, language_hint: str | None
    ) -> object:
        file = (f"chunk-{chunk.index:06d}.wav", chunk.content, "audio/wav")
        try:
            if self._config.transcription_model == "whisper-1":
                if language_hint is None:
                    return await self._client.audio.transcriptions.create(
                        file=file,
                        model="whisper-1",
                        response_format="verbose_json",
                        timestamp_granularities=["segment"],
                        timeout=self._config.transcription_timeout_seconds,
                    )
                return await self._client.audio.transcriptions.create(
                    file=file,
                    model="whisper-1",
                    language=language_hint,
                    response_format="verbose_json",
                    timestamp_granularities=["segment"],
                    timeout=self._config.transcription_timeout_seconds,
                )
            if language_hint is None:
                return await self._client.audio.transcriptions.create(
                    file=file,
                    model=self._config.transcription_model,
                    timeout=self._config.transcription_timeout_seconds,
                )
            return await self._client.audio.transcriptions.create(
                file=file,
                model=self._config.transcription_model,
                language=language_hint,
                timeout=self._config.transcription_timeout_seconds,
            )
        except (OpenAIError, TimeoutError, ValidationError) as error:
            raise provider_error(error) from error


def _validated_chunks(
    chunks: tuple[AudioChunk, ...], maximum_bytes: int
) -> tuple[AudioChunk, ...]:
    if not chunks:
        raise ValueError("audio chunks cannot be empty")
    ordered = tuple(sorted(chunks, key=lambda item: (item.start_ms, item.index)))
    seen: set[int] = set()
    previous_end = 0
    for position, chunk in enumerate(ordered):
        if (
            isinstance(chunk.index, bool)
            or chunk.index < 0
            or chunk.index in seen
            or isinstance(chunk.start_ms, bool)
            or isinstance(chunk.end_ms, bool)
            or chunk.start_ms < 0
            or chunk.end_ms <= chunk.start_ms
            or (position and chunk.start_ms < previous_end)
            or not chunk.content
            or len(chunk.content) > maximum_bytes
        ):
            raise ValueError("audio chunks are invalid")
        seen.add(chunk.index)
        previous_end = chunk.end_ms
    return ordered


def _whisper_segments(
    response: object,
    chunk: AudioChunk,
    existing: list[TranscriptSegment],
) -> list[TranscriptSegment]:
    raw_segments = getattr(response, "segments", None)
    if not isinstance(raw_segments, list) or not raw_segments:
        raise ProviderInvalidResponse()
    language = _language(response, None)
    previous_end = existing[-1].end_ms if existing else chunk.start_ms
    result: list[TranscriptSegment] = []
    for source_position, raw in enumerate(raw_segments):
        text = getattr(raw, "text", None)
        if not isinstance(text, str) or not text.strip():
            continue
        start = _absolute_milliseconds(getattr(raw, "start", None), chunk)
        end = _absolute_milliseconds(getattr(raw, "end", None), chunk)
        start = max(start, previous_end)
        end = min(end, chunk.end_ms)
        if end <= start:
            raise ProviderInvalidResponse()
        segment = TranscriptSegment(
            id=f"segment-{chunk.index:06d}-{source_position:06d}",
            start_ms=start,
            end_ms=end,
            language=language,
            text=text,
        )
        result.append(segment)
        previous_end = end
    if not result:
        raise ProviderInvalidResponse()
    return result


def _chunk_segment(
    response: object, chunk: AudioChunk, language_hint: str | None
) -> TranscriptSegment:
    text = getattr(response, "text", None)
    if not isinstance(text, str) or not text.strip():
        raise ProviderInvalidResponse()
    return TranscriptSegment(
        id=f"segment-{chunk.index:06d}-000000",
        start_ms=chunk.start_ms,
        end_ms=chunk.end_ms,
        language=_language(response, language_hint),
        text=text,
    )


def _language(response: object, hint: str | None) -> str:
    value = getattr(response, "language", None)
    if isinstance(value, str) and value.strip():
        return value.strip()
    if hint is not None and hint.strip():
        return hint.strip()
    return "und"


def _absolute_milliseconds(value: object, chunk: AudioChunk) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not isfinite(value)
        or value < 0
    ):
        raise ProviderInvalidResponse()
    milliseconds = chunk.start_ms + round(value * 1000)
    if milliseconds > chunk.end_ms:
        raise ProviderInvalidResponse()
    return milliseconds
