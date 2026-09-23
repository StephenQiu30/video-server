from __future__ import annotations

import json
import stat
import subprocess
from pathlib import Path

import pytest
from app.services.provider_types import ProviderKey
from app.workers.runner.provider_session_setup import publish_session
from app.workers.runner.provider_startup import (
    BACKEND_ROOT,
    DEFAULT_RUNTIME_ENV,
    DEFAULT_SOURCE_KEY,
    PROJECT_ROOT,
    build_startup_plan,
    main,
    write_runtime_environment,
)
from cryptography.fernet import Fernet


def _cookie(provider: ProviderKey) -> bytes:
    values = {
        ProviderKey.YOUTUBE: (".youtube.com", "SID"),
        ProviderKey.DOUYIN: (".douyin.com", "sessionid"),
        ProviderKey.REDDIT: (".reddit.com", "reddit_session"),
    }
    domain, name = values[provider]
    return (
        "# Netscape HTTP Cookie File\n"
        f"{domain}\tTRUE\t/\tTRUE\t2147483647\t{name}\tfixture-only\n"
    ).encode()


def _values() -> dict[str, str]:
    return {
        "COMPOSE_PROFILES": (
            "youtube-operator,douyin-operator,reddit-operator,wechat-channels-operator"
        ),
        "RUNNER_OPERATOR_BASE_URLS": json.dumps(
            {
                "youtube": "http://youtube-operator-runner:19100",
                "douyin": "http://douyin-operator-runner:19100",
                "reddit": "http://reddit-operator-runner:19100",
                "wechat_channels": "http://wechat-channels-operator-runner:19100",
            }
        ),
        "RUNNER_DEFAULT_ACCESS_POLICIES": json.dumps(
            {
                "youtube": "operator_public",
                "douyin": "operator_public",
                "reddit": "operator_public",
                "wechat_channels": "operator_public",
            }
        ),
        "PROVIDER_CANARY_TARGETS": json.dumps(
            [
                {
                    "target_id": "douyin-public-single",
                    "provider_key": "douyin",
                    "stage": "metadata",
                    "access_mode": "operator_managed",
                    "url": "https://www.douyin.com/video/123",
                }
            ]
        ),
        "PROVIDER_SESSION_DIR": "./sessions",
    }


def test_default_provider_runtime_files_live_under_backend() -> None:
    assert PROJECT_ROOT == BACKEND_ROOT.parent
    assert BACKEND_ROOT.name == "backend"
    assert DEFAULT_RUNTIME_ENV == BACKEND_ROOT / ".local-runtime/provider-startup.env"
    assert DEFAULT_SOURCE_KEY == BACKEND_ROOT / ".local-runtime/provider-source.key"


def test_plan_preserves_routes_even_when_local_sources_are_missing(
    tmp_path: Path,
) -> None:
    publish_session(
        ProviderKey.YOUTUBE,
        tmp_path / "sessions/youtube",
        _cookie(ProviderKey.YOUTUBE),
    )

    plan = build_startup_plan(
        _values(),
    )

    assert set(plan.compose_profiles) == set(_values()["COMPOSE_PROFILES"].split(","))
    assert plan.operator_base_urls == json.loads(_values()["RUNNER_OPERATOR_BASE_URLS"])
    assert plan.default_access_policies == json.loads(
        _values()["RUNNER_DEFAULT_ACCESS_POLICIES"]
    )
    assert plan.canary_targets[0]["access_mode"] == "operator_managed"
    assert all(item.reason == "source_checked_at_runtime" for item in plan.decisions)


def test_plan_does_not_probe_managed_browser_during_startup(tmp_path: Path) -> None:
    values = _values()
    values["COMPOSE_PROFILES"] = "wechat-channels-operator"
    values["RUNNER_OPERATOR_BASE_URLS"] = json.dumps(
        {"wechat_channels": ("http://wechat-channels-operator-runner:19100")}
    )
    values["RUNNER_DEFAULT_ACCESS_POLICIES"] = json.dumps(
        {"wechat_channels": "operator_public"}
    )

    plan = build_startup_plan(
        values,
    )

    assert plan.compose_profiles == ("wechat-channels-operator",)
    assert plan.disabled_local_services == (
        "douyin-operator-runner",
        "qqvideo-operator-runner",
        "reddit-operator-runner",
        "youku-operator-runner",
        "youtube-operator-runner",
    )
    assert plan.operator_base_urls == {
        "wechat_channels": "http://wechat-channels-operator-runner:19100"
    }
    assert plan.decisions[0].reason == "source_checked_at_runtime"


def test_external_operator_endpoint_is_not_treated_as_a_local_source(
    tmp_path: Path,
) -> None:
    values = _values()
    values["COMPOSE_PROFILES"] = ""
    values["RUNNER_OPERATOR_BASE_URLS"] = json.dumps(
        {"reddit": "http://provider-gateway.internal:19100"}
    )
    values["RUNNER_DEFAULT_ACCESS_POLICIES"] = json.dumps({"reddit": "operator_public"})

    plan = build_startup_plan(values)

    assert plan.operator_base_urls == {
        "reddit": "http://provider-gateway.internal:19100"
    }
    assert plan.default_access_policies == {"reddit": "operator_public"}
    assert plan.disabled_local_services == (
        "douyin-operator-runner",
        "qqvideo-operator-runner",
        "reddit-operator-runner",
        "wechat-channels-operator-runner",
        "youku-operator-runner",
        "youtube-operator-runner",
    )
    assert plan.decisions == ()


def test_profile_without_endpoint_fails_configuration_validation(
    tmp_path: Path,
) -> None:
    values = _values()
    values["COMPOSE_PROFILES"] = "douyin-operator"
    values["RUNNER_OPERATOR_BASE_URLS"] = "{}"
    values["RUNNER_DEFAULT_ACCESS_POLICIES"] = "{}"

    with pytest.raises(ValueError, match="needs an endpoint"):
        build_startup_plan(values)


def test_runtime_environment_is_private_and_contains_no_source_material(
    tmp_path: Path,
) -> None:
    plan = build_startup_plan(
        {
            "COMPOSE_PROFILES": "",
            "RUNNER_OPERATOR_BASE_URLS": "{}",
            "RUNNER_DEFAULT_ACCESS_POLICIES": "{}",
            "PROVIDER_CANARY_TARGETS": "[]",
        },
    )
    target = tmp_path / "runtime/provider.env"

    write_runtime_environment(target, plan)

    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    assert "COOKIE" not in target.read_text()
    assert "RUNNER_OPERATOR_BASE_URLS={}" in target.read_text()


def test_configured_local_endpoint_automatically_enables_its_runner() -> None:
    values = _values()
    values["COMPOSE_PROFILES"] = ""
    plan = build_startup_plan(values)
    assert set(plan.compose_profiles) == set(_values()["COMPOSE_PROFILES"].split(","))
    assert plan.operator_base_urls == json.loads(values["RUNNER_OPERATOR_BASE_URLS"])


def test_auto_browser_route_is_declared_even_before_source_is_ready() -> None:
    values = {
        "COMPOSE_PROFILES": "",
        "RUNNER_OPERATOR_BASE_URLS": "{}",
        "RUNNER_DEFAULT_ACCESS_POLICIES": "{}",
    }
    plan = build_startup_plan(
        values, auto_browser_routes=frozenset({ProviderKey.YOUTUBE})
    )
    assert plan.operator_base_urls == {
        "youtube": "http://youtube-operator-runner:19100"
    }
    assert plan.default_access_policies == {"youtube": "operator_public"}
    assert "youtube-operator" in plan.compose_profiles


def test_auto_browser_route_rejects_remote_operator_endpoint() -> None:
    values = {
        "RUNNER_OPERATOR_BASE_URLS": json.dumps(
            {"youtube": "http://remote-operator.internal:19100"}
        ),
        "RUNNER_DEFAULT_ACCESS_POLICIES": "{}",
    }
    with pytest.raises(ValueError, match="local operator"):
        build_startup_plan(values, auto_browser_routes=frozenset({ProviderKey.YOUTUBE}))


def test_start_syncs_host_source_before_compose_and_starts_detached_refresh(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / "deploy.env"
    runtime = tmp_path / "runtime.env"
    compose = tmp_path / "compose.yml"
    env_file.write_text(
        "COMPOSE_PROFILES=\nRUNNER_OPERATOR_BASE_URLS={}\n"
        "RUNNER_DEFAULT_ACCESS_POLICIES={}\n"
        f"PROVIDER_SOURCE_ENCRYPTION_KEY={Fernet.generate_key().decode()}\n"
    )
    compose.write_text("services: {}\n")
    order: list[str] = []

    async def sync(_provider, _settings):
        order.append("source")
        return "ready"

    def run(command, **_kwargs):
        if "config" in command:
            return subprocess.CompletedProcess(command, 0, stdout="api\n")
        order.append("compose")
        return subprocess.CompletedProcess(command, 0)

    def start_detached(**_kwargs):
        order.append("detached")
        return {"youtube": "ready"}

    def disable_legacy():
        order.append("disable_legacy")

    monkeypatch.setattr("app.workers.runner.provider_startup.sys.platform", "darwin")
    monkeypatch.setattr("app.workers.runner.provider_startup.sync_once", sync)
    monkeypatch.setattr("app.workers.runner.provider_startup.subprocess.run", run)
    monkeypatch.setattr(
        "app.workers.runner.provider_startup.start_detached_source_service",
        start_detached,
    )
    monkeypatch.setattr(
        "app.workers.runner.provider_startup.disable_launch_agent", disable_legacy
    )
    assert (
        main(
            [
                "start",
                "--env-file",
                str(env_file),
                "--compose-file",
                str(compose),
                "--runtime-env",
                str(runtime),
            ]
        )
        == 0
    )
    assert order == ["source", "compose", "detached", "disable_legacy"]
    written = runtime.read_text()
    assert 'RUNNER_DEFAULT_ACCESS_POLICIES={"youtube":"operator_public"}' in written
    assert "PROVIDER_SOURCE_ENCRYPTION_KEY=" in written
