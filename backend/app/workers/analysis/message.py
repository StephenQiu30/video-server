from __future__ import annotations

import re
from dataclasses import dataclass
from uuid import UUID

from app.infrastructure.messaging import EventEnvelope, EventEnvelopeError

_SHA256 = re.compile(r"[0-9a-f]{64}")
_FIELDS = {
    "job_id",
    "artifact_id",
    "input_sha256",
    "skill_id",
    "output_language",
    "attempt",
    "version",
}


class AnalysisMessageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AnalysisRequested:
    job_id: UUID
    artifact_id: UUID
    attempt: int
    version: int


def parse_analysis_requested(body: bytes) -> AnalysisRequested:
    try:
        envelope = EventEnvelope.from_bytes(body)
    except EventEnvelopeError as exc:
        raise AnalysisMessageError("invalid event envelope") from exc
    if envelope.event_type != "analysis.requested" or set(envelope.payload) != _FIELDS:
        raise AnalysisMessageError("analysis payload fields do not match schema")
    try:
        job_id = _uuid(envelope.payload["job_id"])
        artifact_id = _uuid(envelope.payload["artifact_id"])
        attempt = _integer(envelope.payload["attempt"])
        version = _integer(envelope.payload["version"])
        sha256 = envelope.payload["input_sha256"]
        labels = tuple(
            envelope.payload[field] for field in ("skill_id", "output_language")
        )
    except (TypeError, ValueError) as exc:
        raise AnalysisMessageError("analysis payload values are invalid") from exc
    if (
        job_id != envelope.aggregate_id
        or not isinstance(sha256, str)
        or _SHA256.fullmatch(sha256) is None
        or any(
            not isinstance(value, str)
            or not value
            or value != value.strip()
            or len(value) > 128
            for value in labels
        )
    ):
        raise AnalysisMessageError("analysis payload values are invalid")
    return AnalysisRequested(job_id, artifact_id, attempt, version)


def _uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise TypeError
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError
    return parsed


def _integer(value: object) -> int:
    if type(value) is not int or value < 0:
        raise ValueError
    return value
