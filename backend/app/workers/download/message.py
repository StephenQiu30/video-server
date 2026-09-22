from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from app.integrations.messaging import EventEnvelope, EventEnvelopeError


class DownloadMessageError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class DownloadRequested:
    job_id: UUID
    attempt: int
    version: int


def parse_download_requested(body: bytes) -> DownloadRequested:
    try:
        envelope = EventEnvelope.from_bytes(body)
    except EventEnvelopeError as exc:
        raise DownloadMessageError("invalid event envelope") from exc
    if envelope.event_type != "download.requested":
        raise DownloadMessageError("unexpected event type")
    if set(envelope.payload) != {"job_id", "attempt", "version"}:
        raise DownloadMessageError("download payload fields do not match schema")
    raw_job_id = envelope.payload["job_id"]
    attempt = envelope.payload["attempt"]
    version = envelope.payload["version"]
    try:
        job_id = UUID(raw_job_id) if isinstance(raw_job_id, str) else None
    except ValueError as exc:
        raise DownloadMessageError("job id is invalid") from exc
    if (
        job_id is None
        or str(job_id) != raw_job_id
        or job_id != envelope.aggregate_id
        or type(attempt) is not int
        or attempt < 0
        or type(version) is not int
        or version < 0
    ):
        raise DownloadMessageError("download payload values are invalid")
    return DownloadRequested(job_id, attempt, version)


def parse_intent_requested(body: bytes) -> UUID:
    try:
        envelope = EventEnvelope.from_bytes(body)
    except EventEnvelopeError as exc:
        raise DownloadMessageError("invalid intent envelope") from exc
    if envelope.event_type != "download.intent.requested" or set(envelope.payload) != {
        "intent_id",
        "version",
    }:
        raise DownloadMessageError("invalid intent event")
    value = envelope.payload["intent_id"]
    version = envelope.payload["version"]
    if value != str(envelope.aggregate_id) or type(version) is not int or version < 0:
        raise DownloadMessageError("invalid intent payload")
    return envelope.aggregate_id
