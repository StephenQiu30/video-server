from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from video_server.errors import DomainError
from video_server.source.rights import RightsCatalog

ROOT = Path(__file__).parents[3]
CATALOG_PATH = ROOT / "config" / "rights-statements.json"
NOW = datetime(2026, 7, 18, 12, 0, tzinfo=UTC)


def _field(value: object, name: str) -> Any:
    if isinstance(value, Mapping):
        return value[name]
    return getattr(value, name)


def _assert_code(error: pytest.ExceptionInfo[DomainError], code: str) -> None:
    assert error.value.code == code


def _entry(
    *,
    version: str,
    locale: str,
    statement: str,
    superseded_at: str | None = None,
) -> dict[str, object]:
    return {
        "version": version,
        "locale": locale,
        "statement": statement,
        "statement_sha256": hashlib.sha256(statement.encode("utf-8")).hexdigest(),
        "effective_at": "2026-07-18T00:00:00Z",
        "expires_at": None,
        "superseded_at": superseded_at,
    }


def _write_catalog(path: Path, entries: list[dict[str, object]]) -> Path:
    path.write_text(
        json.dumps({"schema_version": "1.0", "entries": entries}, ensure_ascii=False),
        encoding="utf-8",
    )
    return path


@pytest.mark.policy
def test_loads_frozen_catalog_and_hashes_exact_utf8_bytes() -> None:
    catalog = RightsCatalog.load(CATALOG_PATH)

    expected_hashes = {
        "zh-CN": "cf7fa670727050ffa2edb508f5adb6bb48907f2c374e375fb2253447a74da15f",
        "en-US": "ef8d7ddcbee41a50c5a3fcc32b4d56e050c551265d587e151934be4826d6ba89",
    }
    for locale, expected_hash in expected_hashes.items():
        statement = catalog.current(locale=locale, now=NOW)
        raw_hash = hashlib.sha256(_field(statement, "statement").encode("utf-8")).hexdigest()
        assert raw_hash == expected_hash
        assert _field(statement, "statement_sha256") == expected_hash
        assert _field(statement, "locale") == locale


@pytest.mark.policy
def test_load_rejects_hash_that_only_matches_unicode_normalized_text(tmp_path: Path) -> None:
    composed = "café"
    decomposed = "cafe\N{COMBINING ACUTE ACCENT}"
    entries = [
        _entry(version="rights-2026-07-18.1", locale="zh-CN", statement=decomposed),
        _entry(version="rights-2026-07-18.1", locale="en-US", statement="English"),
    ]
    entries[0]["statement_sha256"] = hashlib.sha256(composed.encode("utf-8")).hexdigest()

    with pytest.raises(DomainError) as error:
        RightsCatalog.load(_write_catalog(tmp_path / "rights.json", entries))

    _assert_code(error, "RIGHTS_STATEMENT_UNAVAILABLE")


@pytest.mark.parametrize(
    ("locale", "code"),
    [
        (None, "RIGHTS_LOCALE_REQUIRED"),
        ("", "RIGHTS_LOCALE_REQUIRED"),
        ("fr-FR", "RIGHTS_LOCALE_UNSUPPORTED"),
    ],
)
def test_current_requires_a_supported_locale(locale: str | None, code: str) -> None:
    catalog = RightsCatalog.load(CATALOG_PATH)

    with pytest.raises(DomainError) as error:
        catalog.current(locale=locale, now=NOW)

    _assert_code(error, code)


@pytest.mark.policy
def test_attest_rejects_false_confirmation() -> None:
    catalog = RightsCatalog.load(CATALOG_PATH)

    with pytest.raises(DomainError) as error:
        catalog.attest(
            confirmed=False,
            version="rights-2026-07-18.1",
            locale="zh-CN",
            now=NOW,
        )

    _assert_code(error, "RIGHTS_CONFIRMATION_REQUIRED")


@pytest.mark.policy
@pytest.mark.parametrize("version", ["rights-2026-07-17.1", "rights-2026-07-18.99"])
def test_attest_rejects_unknown_or_stale_version(version: str) -> None:
    catalog = RightsCatalog.load(CATALOG_PATH)

    with pytest.raises(DomainError) as error:
        catalog.attest(confirmed=True, version=version, locale="zh-CN", now=NOW)

    _assert_code(error, "RIGHTS_STATEMENT_STALE")


@pytest.mark.policy
def test_attest_rejects_known_version_for_the_wrong_locale(tmp_path: Path) -> None:
    entries = [
        _entry(version="rights-2026-07-18.1", locale="zh-CN", statement="Chinese"),
        _entry(version="rights-2026-07-18.2", locale="en-US", statement="English"),
    ]
    catalog = RightsCatalog.load(_write_catalog(tmp_path / "rights.json", entries))

    with pytest.raises(DomainError) as error:
        catalog.attest(
            confirmed=True,
            version="rights-2026-07-18.2",
            locale="zh-CN",
            now=NOW,
        )

    _assert_code(error, "RIGHTS_STATEMENT_STALE")


@pytest.mark.policy
def test_attest_rejects_superseded_known_version(tmp_path: Path) -> None:
    entries = [
        _entry(
            version="rights-2026-07-18.1",
            locale="zh-CN",
            statement="Old",
            superseded_at="2026-07-18T06:00:00Z",
        ),
        _entry(version="rights-2026-07-18.2", locale="zh-CN", statement="Current"),
        _entry(version="rights-2026-07-18.1", locale="en-US", statement="English"),
    ]
    catalog = RightsCatalog.load(_write_catalog(tmp_path / "rights.json", entries))

    with pytest.raises(DomainError) as error:
        catalog.attest(
            confirmed=True,
            version="rights-2026-07-18.1",
            locale="zh-CN",
            now=NOW,
        )

    _assert_code(error, "RIGHTS_STATEMENT_STALE")


@pytest.mark.policy
def test_attest_returns_the_exact_catalog_identity_and_confirmation_time() -> None:
    catalog = RightsCatalog.load(CATALOG_PATH)

    attestation = catalog.attest(
        confirmed=True,
        version="rights-2026-07-18.1",
        locale="zh-CN",
        now=NOW,
    )

    assert _field(attestation, "version") == "rights-2026-07-18.1"
    assert _field(attestation, "locale") == "zh-CN"
    assert _field(attestation, "statement_sha256") == (
        "cf7fa670727050ffa2edb508f5adb6bb48907f2c374e375fb2253447a74da15f"
    )
    assert _field(attestation, "confirmed_at") == NOW
