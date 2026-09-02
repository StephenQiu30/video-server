from __future__ import annotations

import sys

import pytest
from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner import provider_cookie_boundary as boundary
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
    serialize_export,
)

COOKIE = b"# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tx\n"


def _python(source: str, *args: str) -> tuple[str, ...]:
    return (sys.executable, "-c", source, *args)


@pytest.mark.parametrize(
    "lease",
    (
        ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE),
        ProviderCookieLease(ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED),
        ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE),
    ),
)
def test_parent_accepts_only_exact_typed_export(
    monkeypatch: pytest.MonkeyPatch, lease: ProviderCookieLease
) -> None:
    encoded = serialize_export(lease).hex()
    monkeypatch.setattr(
        boundary,
        "_child_command",
        lambda *args: _python(
            "import sys; sys.stdout.buffer.write(bytes.fromhex(sys.argv[1]))",
            encoded,
        ),
    )

    assert (
        boundary.export_provider_cookie_lease_bounded(
            provider=ProviderKey.YOUTUBE,
            profile="Default",
            version=ProviderSessionVersion.BROWSER,
        )
        == lease
    )


def test_child_calls_typed_provider_export_and_writes_only_status(
    monkeypatch: pytest.MonkeyPatch,
    capfd: pytest.CaptureFixture[str],
) -> None:
    calls: list[tuple[ProviderKey, str, ProviderSessionVersion]] = []

    def export(
        *,
        provider: ProviderKey,
        profile: str,
        version: ProviderSessionVersion,
    ) -> ProviderCookieLease:
        calls.append((provider, profile, version))
        return ProviderCookieLease(ProviderCookieLeaseStatus.CREDENTIAL_REQUIRED)

    monkeypatch.setattr(boundary, "export_provider_cookie_lease", export)

    result = boundary.main(
        (
            "child",
            "--provider",
            "youtube",
            "--profile",
            "Default",
            "--version",
            "browser",
        )
    )

    assert result == 0
    assert calls == [
        (
            ProviderKey.YOUTUBE,
            "Default",
            ProviderSessionVersion.BROWSER,
        )
    ]
    assert capfd.readouterr().out == "credential_required"


def test_command_contains_the_typed_provider_contract() -> None:
    command = boundary._child_command(
        ProviderKey.INSTAGRAM,
        "Default",
        ProviderSessionVersion.BROWSER,
    )

    assert command[:4] == (
        sys.executable,
        "-m",
        "app.runner.provider_cookie_boundary",
        "child",
    )
    assert command[-6:] == (
        "--provider",
        "instagram",
        "--profile",
        "Default",
        "--version",
        "browser",
    )


def test_process_start_failure_is_a_stable_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        boundary.subprocess,
        "Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unavailable")),
    )

    assert boundary.export_provider_cookie_lease_bounded(
        provider=ProviderKey.YOUTUBE,
        profile="Default",
        version=ProviderSessionVersion.BROWSER,
    ) == ProviderCookieLease(ProviderCookieLeaseStatus.SESSION_UNAVAILABLE)
