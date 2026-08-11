from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from app.core.config import Settings
from app.infrastructure.ai_cli import (
    ClaudeCliVideoAnalyzer,
    CliCapabilities,
    CodexCliVideoAnalyzer,
)
from app.workers.analysis import providers
from app.workers.analysis.main import _rabbitmq_worker_url
from app.workers.analysis.providers import (
    authentication_environment,
    build_video_analyzer,
)
from app.workers.analysis.sweeper import AnalysisRecoverySweeper


@pytest.mark.parametrize(
    ("provider", "expected"),
    [("codex", CodexCliVideoAnalyzer), ("claude", ClaudeCliVideoAnalyzer)],
)
def test_worker_builds_selected_oauth_cli_adapter(
    monkeypatch: pytest.MonkeyPatch,
    provider: str,
    expected: type[object],
) -> None:
    def successful_preflight(*args: object, **kwargs: object) -> CliCapabilities:
        del args, kwargs
        return CliCapabilities(
            provider=provider,
            binary=Path(sys.executable),
            version="controlled",
            ffmpeg=Path(sys.executable),
            ffprobe=Path(sys.executable),
        )

    monkeypatch.setattr(providers, "preflight", successful_preflight)
    settings = Settings(app_env="test", analysis_cli_provider=provider)

    runtime = build_video_analyzer(settings)

    assert isinstance(runtime.analyzer, expected)
    assert runtime.provider == provider
    assert runtime.cli_version == "controlled"


def test_worker_discards_api_key_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "must-not-be-used")
    monkeypatch.setenv("ANTHROPIC_AUTH_TOKEN", "must-not-be-used")

    environment = authentication_environment()

    assert "OPENAI_API_KEY" not in environment
    assert "ANTHROPIC_AUTH_TOKEN" not in environment
    assert "HOME" in environment
    if sys.platform == "win32":
        assert environment["SYSTEMROOT"] == os.environ["SYSTEMROOT"]
        if "WINDIR" in os.environ:
            assert environment["WINDIR"] == os.environ["WINDIR"]


def test_worker_uses_the_declared_shared_rabbitmq_vhost() -> None:
    result = _rabbitmq_worker_url("amqp://analysis:secret@localhost:5673/", "video")

    assert result == "amqp://analysis:secret@localhost:5673/video"


class FakeRecovery:
    def __init__(self) -> None:
        self.queued = (uuid4(),)
        self.stale = (uuid4(),)
        self.ready = (uuid4(),)
        self.calls: list[tuple[str, int]] = []

    async def recover_stale_queued(
        self, now: datetime, stale_before: datetime, *, limit: int = 100
    ) -> tuple[object, ...]:
        assert stale_before < now
        self.calls.append(("queued", limit))
        return self.queued

    async def reclaim_stale(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[object, ...]:
        self.calls.append(("stale", limit))
        return self.stale

    async def release_ready_retries(
        self, now: datetime, *, limit: int = 100
    ) -> tuple[object, ...]:
        self.calls.append(("ready", limit))
        return self.ready


@pytest.mark.asyncio
async def test_recovery_sweeper_reclaims_then_requeues_ready_jobs() -> None:
    repository = FakeRecovery()
    now = datetime(2026, 8, 6, tzinfo=UTC)
    sweeper = AnalysisRecoverySweeper(
        repository,  # type: ignore[arg-type]
        lambda: now,
    )

    assert await sweeper.tick() == (
        repository.queued,
        repository.stale,
        repository.ready,
    )
    assert repository.calls == [("queued", 100), ("stale", 100), ("ready", 100)]
