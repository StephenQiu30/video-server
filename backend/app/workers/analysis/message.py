from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.infrastructure.messaging import EventEnvelope, EventEnvelopeError

_FIELDS = {
    "job_id",
    "run_id",
    "run_no",
    "version",
}


class AnalysisMessageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AnalysisRequested:
    job_id: UUID
    run_id: UUID
    run_no: int
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
        run_id = _uuid(envelope.payload["run_id"])
        run_no = _integer(envelope.payload["run_no"], positive=True)
        version = _integer(envelope.payload["version"])
    except (TypeError, ValueError) as exc:
        raise AnalysisMessageError("analysis payload values are invalid") from exc
    if job_id != envelope.aggregate_id:
        raise AnalysisMessageError("analysis payload values are invalid")
    return AnalysisRequested(job_id, run_id, run_no, version)


def _uuid(value: object) -> UUID:
    if not isinstance(value, str):
        raise TypeError
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError
    return parsed


def _integer(value: object, *, positive: bool = False) -> int:
    if type(value) is not int or value < (1 if positive else 0):
        raise ValueError
    return value
