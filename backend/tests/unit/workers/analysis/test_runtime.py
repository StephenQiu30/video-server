from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from app.application.ai_providers import (
    AiProviderAuthMode,
    AiProviderEngine,
    AiProviderProfile,
)
from app.core.config import Settings
from app.infrastructure.ai_cli import (
    ClaudeCliVideoAnalyzer,
    CliCapabilities,
    CodexAppServerVideoAnalyzer,
)
from app.infrastructure.ai_deepseek import LangChainDeepSeekAnalyzer
from app.workers.analysis import profile_runtime
from app.workers.analysis.main import _rabbitmq_worker_url
from app.workers.analysis.providers import (
    ConfiguredAnalyzerResolver,
    authentication_environment,
    build_video_analyzer,
)
from app.workers.analysis.sweeper import AnalysisRecoverySweeper


@pytest.mark.parametrize(
    ("provider", "expected"),
    [("codex", CodexAppServerVideoAnalyzer), ("claude", ClaudeCliVideoAnalyzer)],
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

    monkeypatch.setattr(profile_runtime, "preflight", successful_preflight)
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


@pytest.mark.asyncio
async def test_active_api_provider_is_injected_only_into_selected_cli_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[bool] = []

    def successful_preflight(*args: object, **kwargs: object) -> CliCapabilities:
        del args
        calls.append(bool(kwargs["verify_authentication"]))
        return CliCapabilities(
            provider="codex",
            binary=Path(sys.executable),
            version="controlled",
            ffmpeg=Path(sys.executable),
            ffprobe=Path(sys.executable),
        )

    class Repository:
        async def get_active_profile(self) -> AiProviderProfile:
            return AiProviderProfile(
                key="custom",
                display_name="Custom Provider",
                engine=AiProviderEngine.CODEX,
                auth_mode=AiProviderAuthMode.API_KEY,
                base_url="https://api.example.com/v1",
                model="gpt-custom",
                credential_ciphertext=b"ciphertext",
                credential_key_id="fernet-test",
                is_active=True,
                created_at=datetime(2026, 8, 13, tzinfo=UTC),
                updated_at=datetime(2026, 8, 13, tzinfo=UTC),
            )

    class Cipher:
        def decrypt(self, provider_key: str, ciphertext: bytes, key_id: str) -> str:
            assert (provider_key, ciphertext, key_id) == (
                "custom",
                b"ciphertext",
                "fernet-test",
            )
            return "secret-value"

    monkeypatch.setattr(profile_runtime, "preflight", successful_preflight)
    resolver = ConfiguredAnalyzerResolver(
        Settings(app_env="test"),
        Repository(),  # type: ignore[arg-type]
        Cipher(),  # type: ignore[arg-type]
    )

    selection = await resolver.resolve()
    again = await resolver.resolve()

    assert selection is again
    assert selection.provider == "custom"
    config = selection.analyzer._config  # type: ignore[attr-defined]
    assert dict(config.extra_environment) == {
        "VIDEO_ANALYSIS_PROVIDER_KEY": "secret-value"
    }
    assert any("api.example.com" in value for value in config.provider_arguments)
    assert all("secret-value" not in value for value in config.provider_arguments)
    assert calls == [False]


@pytest.mark.asyncio
async def test_updated_active_profile_rebuilds_adapter_for_next_task(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    updated_at = datetime(2026, 8, 13, tzinfo=UTC)

    def successful_preflight(*args: object, **kwargs: object) -> CliCapabilities:
        del args, kwargs
        calls.append("preflight")
        return CliCapabilities(
            provider="codex",
            binary=Path(sys.executable),
            version="controlled",
            ffmpeg=Path(sys.executable),
            ffprobe=Path(sys.executable),
        )

    class Repository:
        model = "model-a"
        secret = b"cipher-a"
        changed_at = updated_at

        async def get_active_profile(self) -> AiProviderProfile:
            return AiProviderProfile(
                key="custom",
                display_name="Custom Provider",
                engine=AiProviderEngine.CODEX,
                auth_mode=AiProviderAuthMode.API_KEY,
                base_url="https://api.example.com/v1",
                model=self.model,
                credential_ciphertext=self.secret,
                credential_key_id="fernet-test",
                is_active=True,
                created_at=updated_at,
                updated_at=self.changed_at,
            )

    class Cipher:
        def decrypt(self, provider_key: str, ciphertext: bytes, key_id: str) -> str:
            assert provider_key == "custom" and key_id == "fernet-test"
            return ciphertext.decode()

    repository = Repository()
    monkeypatch.setattr(profile_runtime, "preflight", successful_preflight)
    resolver = ConfiguredAnalyzerResolver(
        Settings(app_env="test"),
        repository,  # type: ignore[arg-type]
        Cipher(),  # type: ignore[arg-type]
    )

    first = await resolver.resolve()
    repository.model = "model-b"
    repository.secret = b"cipher-b"
    repository.changed_at = datetime(2026, 8, 14, tzinfo=UTC)
    second = await resolver.resolve()

    assert second is not first
    assert (first.model, second.model) == ("model-a", "model-b")
    assert dict(second.analyzer._config.extra_environment) == {  # type: ignore[attr-defined]
        "VIDEO_ANALYSIS_PROVIDER_KEY": "cipher-b"
    }
    assert calls == ["preflight", "preflight"]


@pytest.mark.asyncio
async def test_deepseek_profile_uses_web_secret_and_media_tools_without_cli_login(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    now = datetime(2026, 8, 29, tzinfo=UTC)

    class Repository:
        async def get_active_profile(self) -> AiProviderProfile:
            return AiProviderProfile(
                key="deepseek-main",
                display_name="DeepSeek 主线路",
                engine=AiProviderEngine.DEEPSEEK,
                auth_mode=AiProviderAuthMode.API_KEY,
                base_url="https://api.deepseek.com",
                model="deepseek-v4-flash-vision-exp",
                credential_ciphertext=b"ciphertext",
                credential_key_id="fernet-test",
                is_active=True,
                created_at=now,
                updated_at=now,
            )

    class Cipher:
        def decrypt(self, provider_key: str, ciphertext: bytes, key_id: str) -> str:
            assert (provider_key, ciphertext, key_id) == (
                "deepseek-main",
                b"ciphertext",
                "fernet-test",
            )
            return "web-managed-secret"

    media_calls: list[dict[str, object]] = []

    def media_preflight(**kwargs: object) -> tuple[Path, Path]:
        media_calls.append(kwargs)
        return Path(sys.executable), Path(sys.executable)

    monkeypatch.setattr(profile_runtime, "media_preflight", media_preflight)
    resolver = ConfiguredAnalyzerResolver(
        Settings(app_env="test"),
        Repository(),  # type: ignore[arg-type]
        Cipher(),  # type: ignore[arg-type]
    )

    selection = await resolver.resolve()

    assert isinstance(selection.analyzer, LangChainDeepSeekAnalyzer)
    assert selection.provider == "deepseek-main"
    assert selection.model == "deepseek-v4-flash-vision-exp"
    assert selection.cli_version.startswith("langchain-deepseek/")
    assert len(media_calls) == 1
    assert "web-managed-secret" not in repr(selection.analyzer._model)  # type: ignore[attr-defined]


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
