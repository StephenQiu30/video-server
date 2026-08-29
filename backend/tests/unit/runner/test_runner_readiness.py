from __future__ import annotations

from pathlib import Path

import pytest
from api_helpers import settings
from app.runner import readiness
from app.runner.readiness import RunnerReadiness


@pytest.mark.asyncio
async def test_runner_readiness_checks_binaries_workspace_proxy_and_pot(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    configured = settings(tmp_path).model_copy(
        update={
            "runner_youtube_pot_base_url": "http://youtube-pot-provider:4416",
        }
    )
    endpoints: list[str] = []

    async def tcp_ready(url: str) -> bool:
        endpoints.append(url)
        return True

    monkeypatch.setattr(readiness, "_tcp_ready", tcp_ready)
    probe = RunnerReadiness(configured, binary_exists=lambda binary: binary)

    assert await probe.check() is True
    assert endpoints == [
        configured.runner_egress_proxy,
        "http://youtube-pot-provider:4416",
    ]


@pytest.mark.asyncio
async def test_runner_readiness_fails_when_a_dependency_is_missing(
    tmp_path: Path,
) -> None:
    missing_binary = RunnerReadiness(
        settings(tmp_path),
        binary_exists=lambda binary: None if binary == "yt-dlp" else binary,
    )
    missing_workspace = RunnerReadiness(
        settings(tmp_path / "missing"),
        binary_exists=lambda binary: binary,
    )
    missing_session = RunnerReadiness(
        settings(tmp_path),
        binary_exists=lambda binary: binary,
        session_ready=lambda: False,
    )

    assert await missing_binary.check() is False
    assert await missing_workspace.check() is False
    assert await missing_session.check() is False
