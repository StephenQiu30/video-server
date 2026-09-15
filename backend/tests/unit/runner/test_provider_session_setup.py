from __future__ import annotations

import stat
from pathlib import Path

import pytest
from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner import provider_session_setup as setup
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_file import ProviderCookieFile
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
)
from app.runner.provider_session_setup import publish_session

COOKIE = (
    b"# Netscape HTTP Cookie File\n"
    b".youtube.com\tTRUE\t/\tTRUE\t2147483647\tSID\tfixture-only\n"
)


def test_capture_uses_selected_existing_profile_once(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    calls: list[dict[str, object]] = []

    def export(**kwargs: object) -> ProviderCookieLease:
        calls.append(kwargs)
        return ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE)

    monkeypatch.setattr(setup, "export_provider_cookie_lease_bounded", export)
    setup.capture_chrome_session(
        ProviderKey.YOUTUBE, tmp_path / "source", profile="Profile 2"
    )
    assert calls == [
        {
            "provider": ProviderKey.YOUTUBE,
            "profile": "Profile 2",
            "version": ProviderSessionVersion.BROWSER,
        }
    ]
    assert capsys.readouterr().out == ""
    assert (tmp_path / "source" / "cookies.txt").read_bytes() == COOKIE


def test_denied_capture_does_not_replace_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "source"
    publish_session(ProviderKey.YOUTUBE, root, COOKIE)
    monkeypatch.setattr(
        setup,
        "export_provider_cookie_lease_bounded",
        lambda **kwargs: ProviderCookieLease(
            ProviderCookieLeaseStatus.PERMISSION_DENIED
        ),
    )
    with pytest.raises(RunnerFailure) as caught:
        setup.capture_chrome_session(ProviderKey.YOUTUBE, root)
    assert caught.value.code == "provider_session_permission_denied"
    assert (root / "cookies.txt").read_bytes() == COOKIE


def test_publish_can_replace_without_chrome_and_preserves_private_modes(
    tmp_path: Path,
) -> None:
    root = tmp_path / "source"
    publish_session(ProviderKey.YOUTUBE, root, COOKIE)
    assert stat.S_IMODE(root.stat().st_mode) == 0o700
    assert stat.S_IMODE((root / "cookies.txt").stat().st_mode) == 0o600
    replacement = COOKIE.replace(b"fixture-only", b"replacement")
    publish_session(ProviderKey.YOUTUBE, root, replacement)
    assert (
        ProviderCookieFile(root / "cookies.txt").read(
            ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER
        )
        == replacement
    )
    assert sorted(p.name for p in root.iterdir()) == [".publish.lock", "cookies.txt"]


@pytest.mark.parametrize(
    "payload",
    [
        b"invalid",
        COOKIE.replace(b"youtube.com", b"example.com"),
        COOKIE.replace(b"2147483647", b"1"),
    ],
)
def test_invalid_replacement_preserves_previous_source(
    tmp_path: Path, payload: bytes
) -> None:
    root = tmp_path / "source"
    publish_session(ProviderKey.YOUTUBE, root, COOKIE)
    with pytest.raises(RunnerFailure):
        publish_session(ProviderKey.YOUTUBE, root, payload)
    assert (root / "cookies.txt").read_bytes() == COOKIE


def test_rejects_symlink_parent(tmp_path: Path) -> None:
    actual = tmp_path / "actual"
    actual.mkdir()
    link = tmp_path / "link"
    link.symlink_to(actual, target_is_directory=True)
    with pytest.raises(OSError):
        publish_session(ProviderKey.YOUTUBE, link / "source", COOKIE)
    assert not (actual / "source").exists()


def test_failed_atomic_replace_keeps_old_source(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "source"
    publish_session(ProviderKey.YOUTUBE, root, COOKIE)

    def fail(*args: object) -> None:
        raise OSError("fixture disk failure")

    monkeypatch.setattr(setup.os, "replace", fail)
    with pytest.raises(OSError):
        publish_session(
            ProviderKey.YOUTUBE, root, COOKIE.replace(b"fixture-only", b"new")
        )
    assert (root / "cookies.txt").read_bytes() == COOKIE
    assert not list(root.glob(".cookies-*"))
