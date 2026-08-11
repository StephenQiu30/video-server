from __future__ import annotations

from pathlib import Path

import pytest
from app.runner.settings import RunnerSettings
from pydantic import ValidationError

SECRET = "runner-shared-secret-material-at-least-32-bytes"


def test_proxy_and_hmac_secret_are_required_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        RunnerSettings(
            runner_hmac_secret=SECRET,
            runner_workspace_root=tmp_path,
        )


def test_loads_minimal_runner_environment(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("RUNNER_HMAC_SECRET", SECRET)
    monkeypatch.setenv("RUNNER_EGRESS_PROXY", "http://egress-proxy:3128")
    monkeypatch.setenv("RUNNER_WORKSPACE_ROOT", str(tmp_path))

    settings = RunnerSettings()

    assert settings.hmac_secret_bytes == SECRET.encode()
    assert settings.runner_egress_proxy == "http://egress-proxy:3128"
    assert settings.runner_provider_egress_proxies == {}
    assert settings.runner_workspace_root == tmp_path.resolve()


def test_loads_credential_free_provider_proxy_overrides(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("RUNNER_HMAC_SECRET", SECRET)
    monkeypatch.setenv("RUNNER_EGRESS_PROXY", "http://egress-proxy:3128")
    monkeypatch.setenv(
        "RUNNER_PROVIDER_EGRESS_PROXIES",
        '{"youtube":"http://youtube-egress:3128"}',
    )
    monkeypatch.setenv("RUNNER_WORKSPACE_ROOT", str(tmp_path))

    settings = RunnerSettings()

    assert settings.egress_proxy_for("youtube") == "http://youtube-egress:3128"
    assert settings.egress_proxy_for("bilibili") == "http://egress-proxy:3128"


def test_runner_uses_the_same_exact_peertube_instance_allowlist(
    tmp_path: Path,
) -> None:
    settings = RunnerSettings(
        runner_hmac_secret=SECRET,
        runner_egress_proxy="http://egress-proxy:3128",
        runner_workspace_root=tmp_path,
        peertube_allowed_instances=frozenset({"VIDEO.EXAMPLE.COM"}),
    )

    assert settings.peertube_allowed_instances == frozenset({"video.example.com"})
    with pytest.raises(ValidationError, match="invalid host"):
        RunnerSettings(
            runner_hmac_secret=SECRET,
            runner_egress_proxy="http://egress-proxy:3128",
            runner_workspace_root=tmp_path,
            peertube_allowed_instances=frozenset({"*.example.com"}),
        )


@pytest.mark.parametrize(
    "proxy",
    [
        "socks5://egress-proxy:1080",
        "http://user:password@egress-proxy:3128",
        "http:///missing-host",
        "http://egress-proxy:3128/path",
    ],
)
def test_rejects_unsafe_proxy_configuration(proxy: str, tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        RunnerSettings(
            runner_hmac_secret=SECRET,
            runner_egress_proxy=proxy,
            runner_workspace_root=tmp_path,
        )


def test_rejects_provider_proxy_credentials(tmp_path: Path) -> None:
    with pytest.raises(ValidationError):
        RunnerSettings(
            runner_hmac_secret=SECRET,
            runner_egress_proxy="http://egress-proxy:3128",
            runner_provider_egress_proxies={
                "youtube": "http://user:secret@youtube-egress:3128"
            },
            runner_workspace_root=tmp_path,
        )
