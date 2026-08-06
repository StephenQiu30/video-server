from __future__ import annotations

from dataclasses import dataclass

from app.domain.analysis.enums import AnalysisValidationCode
from app.domain.analysis.errors import AnalysisValidationError
from app.domain.analysis.text import identifier, non_negative_integer, required_text


@dataclass(frozen=True, slots=True)
class TranscriptSegment:
    id: str
    start_ms: int
    end_ms: int
    language: str
    text: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", identifier(self.id, "segment id"))
        start = non_negative_integer(self.start_ms, "segment start_ms")
        end = non_negative_integer(self.end_ms, "segment end_ms")
        if end <= start:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_TIME_RANGE,
                "segment end_ms must be greater than start_ms",
            )
        object.__setattr__(
            self, "language", required_text(self.language, "language", maximum=35)
        )
        object.__setattr__(self, "text", required_text(self.text, "text"))


@dataclass(frozen=True, slots=True)
class Transcript:
    segments: tuple[TranscriptSegment, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.segments, tuple) or not self.segments:
            raise AnalysisValidationError(
                AnalysisValidationCode.INVALID_SCHEMA,
                "transcript must contain segments",
            )
        seen: set[str] = set()
        previous_end = 0
        for position, segment in enumerate(self.segments):
            if not isinstance(segment, TranscriptSegment):
                raise AnalysisValidationError(
                    AnalysisValidationCode.INVALID_SCHEMA,
                    "transcript contains an invalid segment",
                )
            if segment.id in seen:
                raise AnalysisValidationError(
                    AnalysisValidationCode.DUPLICATE_IDENTIFIER,
                    f"duplicate transcript segment id: {segment.id}",
                )
            if position and segment.start_ms < previous_end:
                raise AnalysisValidationError(
                    AnalysisValidationCode.INVALID_TIME_RANGE,
                    "transcript segments must be monotonic and non-overlapping",
                )
            seen.add(segment.id)
            previous_end = segment.end_ms

    @property
    def duration_ms(self) -> int:
        return self.segments[-1].end_ms

    def segment(self, segment_id: str) -> TranscriptSegment:
        for segment in self.segments:
            if segment.id == segment_id:
                return segment
        raise AnalysisValidationError(
            AnalysisValidationCode.INVALID_EVIDENCE,
            f"unknown transcript segment id: {segment_id}",
        )
