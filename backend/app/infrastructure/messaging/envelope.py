"""Versioned JSON event envelope with sensitive-data containment."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Self, cast
from uuid import UUID

type JsonValue = (
    None | bool | int | float | str | list[JsonValue] | dict[str, JsonValue]
)

_EVENT_TYPE = re.compile(r"^[a-z][a-z0-9_.-]{0,127}$")
_URL_VALUE = re.compile(r"(?i)\bhttps?://")
_FORBIDDEN_KEY_PARTS = {
    "authorization",
    "ciphertext",
    "cookie",
    "cookies",
    "credential",
    "credentials",
    "key",
    "password",
    "secret",
    "session",
    "token",
}
_ENVELOPE_FIELDS = {
    "schema_version",
    "event_id",
    "aggregate_id",
    "event_type",
    "occurred_at",
    "payload",
}
_MAX_PAYLOAD_BYTES = 64 * 1024
_MAX_DEPTH = 8


class EventEnvelopeError(ValueError):
    """The event is malformed or attempts to carry sensitive data."""


@dataclass(frozen=True, slots=True)
class EventEnvelope:
    schema_version: int
    event_id: UUID
    aggregate_id: UUID
    event_type: str
    occurred_at: datetime
    payload: dict[str, JsonValue]

    def __post_init__(self) -> None:
        if type(self.schema_version) is not int or self.schema_version != 1:
            raise EventEnvelopeError("unsupported schema version")
        if not isinstance(self.event_id, UUID) or not isinstance(
            self.aggregate_id, UUID
        ):
            raise EventEnvelopeError("event and aggregate ids must be UUIDs")
        if (
            not isinstance(self.event_type, str)
            or _EVENT_TYPE.fullmatch(self.event_type) is None
        ):
            raise EventEnvelopeError("invalid event type")
        if self.occurred_at.tzinfo is None or self.occurred_at.utcoffset() is None:
            raise EventEnvelopeError("occurred_at must be timezone-aware")
        normalized_time = self.occurred_at.astimezone(UTC)
        normalized_payload = _validate_payload(self.payload)
        object.__setattr__(self, "occurred_at", normalized_time)
        object.__setattr__(self, "payload", normalized_payload)

    def to_bytes(self) -> bytes:
        document: dict[str, object] = {
            "schema_version": self.schema_version,
            "event_id": str(self.event_id),
            "aggregate_id": str(self.aggregate_id),
            "event_type": self.event_type,
            "occurred_at": _format_time(self.occurred_at),
            "payload": self.payload,
        }
        return json.dumps(
            document,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        ).encode()

    @classmethod
    def from_bytes(cls, encoded: bytes) -> Self:
        try:
            document = json.loads(encoded, object_pairs_hook=_unique_object)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise EventEnvelopeError("event is not valid JSON") from exc
        if not isinstance(document, dict) or set(document) != _ENVELOPE_FIELDS:
            raise EventEnvelopeError("event envelope fields do not match schema")
        try:
            event_id = _uuid(document["event_id"])
            aggregate_id = _uuid(document["aggregate_id"])
            occurred_at = _time(document["occurred_at"])
        except (KeyError, TypeError, ValueError) as exc:
            raise EventEnvelopeError("event envelope values are invalid") from exc
        payload = document["payload"]
        if not isinstance(payload, dict):
            raise EventEnvelopeError("payload must be an object")
        return cls(
            schema_version=cast(int, document["schema_version"]),
            event_id=event_id,
            aggregate_id=aggregate_id,
            event_type=cast(str, document["event_type"]),
            occurred_at=occurred_at,
            payload=cast(dict[str, JsonValue], payload),
        )


def _validate_payload(value: object) -> dict[str, JsonValue]:
    if not isinstance(value, dict):
        raise EventEnvelopeError("payload must be an object")
    normalized = cast(dict[str, JsonValue], _validate_value(value, 0))
    encoded = json.dumps(normalized, separators=(",", ":"), ensure_ascii=True).encode()
    if len(encoded) > _MAX_PAYLOAD_BYTES:
        raise EventEnvelopeError("payload exceeds size limit")
    return normalized


def _validate_value(value: object, depth: int) -> JsonValue:
    if depth > _MAX_DEPTH:
        raise EventEnvelopeError("payload exceeds nesting limit")
    if value is None or isinstance(value, bool | int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EventEnvelopeError("payload number must be finite")
        return value
    if isinstance(value, str):
        if len(value) > 4096 or _URL_VALUE.search(value):
            raise EventEnvelopeError("payload string is unsafe")
        return value
    if isinstance(value, list):
        if len(value) > 1000:
            raise EventEnvelopeError("payload list exceeds item limit")
        return [_validate_value(item, depth + 1) for item in value]
    if isinstance(value, dict):
        if len(value) > 1000:
            raise EventEnvelopeError("payload object exceeds item limit")
        result: dict[str, JsonValue] = {}
        for key, item in value.items():
            if not isinstance(key, str) or not key or len(key) > 128:
                raise EventEnvelopeError("payload key is invalid")
            if _sensitive_key(key):
                raise EventEnvelopeError("payload contains a forbidden field")
            result[key] = _validate_value(item, depth + 1)
        return result
    raise EventEnvelopeError("payload contains a non-JSON value")


def _sensitive_key(key: str) -> bool:
    expanded = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", key)
    normalized = re.sub(r"[^a-z0-9]+", "_", expanded.casefold()).strip("_")
    parts = set(normalized.split("_"))
    return (
        "url" in parts
        or bool(parts & _FORBIDDEN_KEY_PARTS)
        or normalized in {"api_key", "provider_key", "access_key"}
    )


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise EventEnvelopeError("event contains a duplicate JSON key")
        result[key] = value
    return result


def _uuid(value: Any) -> UUID:
    if not isinstance(value, str):
        raise TypeError("UUID must be a string")
    parsed = UUID(value)
    if str(parsed) != value:
        raise ValueError("UUID must use canonical form")
    return parsed


def _format_time(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _time(value: Any) -> datetime:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise ValueError("timestamp must be UTC")
    parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    return parsed.astimezone(UTC)
