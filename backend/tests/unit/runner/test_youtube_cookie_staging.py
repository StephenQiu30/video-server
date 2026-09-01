from __future__ import annotations

import stat
from pathlib import Path

import pytest
from app.runner import youtube_cookie_staging as staging


def test_publish_replaces_a_stale_private_staging_file(tmp_path: Path) -> None:
    version = "chrome-default"
    stale = staging.create_cookie_staging(tmp_path, version)
    stale.write_bytes(b"stale-canary")

    active = staging.create_cookie_staging(tmp_path, version)
    staging.publish_cookie_payload(tmp_path, version, b"fresh-payload", active)

    target = tmp_path / f"{version}.cookies.txt"
    assert target.read_bytes() == b"fresh-payload"
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert not active.exists()


def test_publish_failure_removes_the_sensitive_staging_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    version = "chrome-default"
    active = staging.create_cookie_staging(tmp_path, version)

    def fail(descriptor: int) -> None:
        del descriptor
        raise OSError("synthetic fsync failure")

    monkeypatch.setattr(staging.os, "fsync", fail)

    with pytest.raises(OSError, match="synthetic fsync"):
        staging.publish_cookie_payload(tmp_path, version, b"private-canary", active)

    assert not active.exists()
    assert not (tmp_path / f"{version}.cookies.txt").exists()


def test_publish_rejects_an_unexpected_staging_path(tmp_path: Path) -> None:
    unexpected = tmp_path / "unexpected"
    unexpected.write_bytes(b"")

    with pytest.raises(OSError, match="unsafe Cookie staging"):
        staging.publish_cookie_payload(
            tmp_path,
            "chrome-default",
            b"private-canary",
            unexpected,
        )

    assert unexpected.read_bytes() == b""
