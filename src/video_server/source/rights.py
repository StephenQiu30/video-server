"""Versioned rights-statement catalog boundary."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker  # type: ignore[import-untyped]

from video_server.errors import DomainError


class RightsCatalogError(DomainError):
    """The rights catalog or submitted attestation is invalid."""


@dataclass(frozen=True, slots=True)
class RightsStatement:
    version: str
    locale: str
    statement: str
    statement_sha256: str
    effective_at: datetime
    expires_at: datetime | None


@dataclass(frozen=True, slots=True)
class RightsAttestation:
    version: str
    locale: str
    statement_sha256: str
    confirmed_at: datetime


@dataclass(frozen=True, slots=True)
class _CatalogEntry:
    statement: RightsStatement
    superseded_at: datetime | None


def _catalog_error(
    code: str = "RIGHTS_STATEMENT_UNAVAILABLE",
    detail: str = "The current rights statement is unavailable.",
) -> RightsCatalogError:
    return RightsCatalogError(
        code,
        detail,
        retryable=code == "RIGHTS_STATEMENT_UNAVAILABLE",
        actions=("refresh_rights_statement",) if code == "RIGHTS_STATEMENT_STALE" else None,
    )


def _parse_datetime(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("timezone required")
    return parsed


class RightsCatalog:
    """Immutable catalog facade; implementation validates hashes and lifecycle."""

    _SUPPORTED_LOCALES = frozenset({"zh-CN", "en-US"})

    def __init__(self, entries: tuple[_CatalogEntry, ...]) -> None:
        self._entries = entries

    @classmethod
    def load(cls, path: str | Path) -> RightsCatalog:
        try:
            payload = json.loads(Path(path).read_text(encoding="utf-8"))
            if not isinstance(payload, Mapping):
                raise ValueError("catalog must be an object")
            return cls.from_mapping(payload)
        except RightsCatalogError:
            raise
        except (OSError, UnicodeError, ValueError, TypeError):
            raise _catalog_error() from None

    def current(self, locale: str | None, *, now: datetime) -> RightsStatement:
        if not locale:
            raise _catalog_error("RIGHTS_LOCALE_REQUIRED", "A rights-statement locale is required.")
        if locale not in self._SUPPORTED_LOCALES:
            raise _catalog_error(
                "RIGHTS_LOCALE_UNSUPPORTED",
                "The requested rights-statement locale is not supported.",
            )
        if now.tzinfo is None or now.utcoffset() is None:
            raise _catalog_error()
        current = [
            entry.statement
            for entry in self._entries
            if entry.statement.locale == locale
            and entry.statement.effective_at <= now
            and (entry.statement.expires_at is None or now < entry.statement.expires_at)
            and (entry.superseded_at is None or now < entry.superseded_at)
        ]
        if len(current) != 1:
            raise _catalog_error()
        return current[0]

    def attest(
        self,
        *,
        confirmed: bool,
        version: str,
        locale: str,
        now: datetime,
    ) -> RightsAttestation:
        if not confirmed:
            raise _catalog_error(
                "RIGHTS_CONFIRMATION_REQUIRED",
                "Rights confirmation is required before source resolution.",
            )
        statement = self.current(locale, now=now)
        if statement.version != version:
            raise _catalog_error(
                "RIGHTS_STATEMENT_STALE",
                "The submitted rights statement is no longer current.",
            )
        return RightsAttestation(
            version=statement.version,
            locale=statement.locale,
            statement_sha256=statement.statement_sha256,
            confirmed_at=now,
        )

    @classmethod
    def from_mapping(cls, payload: Mapping[str, Any]) -> RightsCatalog:
        try:
            schema_path = (
                Path(__file__).resolve().parents[3]
                / "schemas"
                / ("rights-statement-catalog.schema.json")
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
            validator = Draft202012Validator(schema, format_checker=FormatChecker())
            if next(validator.iter_errors(payload), None) is not None:
                raise ValueError("catalog schema validation failed")

            parsed_entries: list[_CatalogEntry] = []
            identities: set[tuple[str, str]] = set()
            for raw_entry in payload["entries"]:
                identity = (raw_entry["version"], raw_entry["locale"])
                if identity in identities:
                    raise ValueError("duplicate catalog identity")
                identities.add(identity)
                statement = raw_entry["statement"]
                expected_hash = hashlib.sha256(statement.encode("utf-8")).hexdigest()
                if raw_entry["statement_sha256"] != expected_hash:
                    raise ValueError("statement hash mismatch")
                effective_at = _parse_datetime(raw_entry["effective_at"])
                expires_at = (
                    _parse_datetime(raw_entry["expires_at"])
                    if raw_entry["expires_at"] is not None
                    else None
                )
                superseded_at = (
                    _parse_datetime(raw_entry["superseded_at"])
                    if raw_entry["superseded_at"] is not None
                    else None
                )
                if (expires_at is not None and expires_at <= effective_at) or (
                    superseded_at is not None and superseded_at <= effective_at
                ):
                    raise ValueError("invalid catalog lifecycle")
                parsed_entries.append(
                    _CatalogEntry(
                        RightsStatement(
                            version=identity[0],
                            locale=identity[1],
                            statement=statement,
                            statement_sha256=expected_hash,
                            effective_at=effective_at,
                            expires_at=expires_at,
                        ),
                        superseded_at,
                    )
                )
            return cls(tuple(parsed_entries))
        except RightsCatalogError:
            raise
        except (KeyError, OSError, UnicodeError, ValueError, TypeError):
            raise _catalog_error() from None
