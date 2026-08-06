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
    assert settings.runner_workspace_root == tmp_path.resolve()


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
