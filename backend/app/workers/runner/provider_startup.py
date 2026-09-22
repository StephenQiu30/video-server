"""Preserve declared Provider routes across temporary source outages."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

from app.services.provider_types import ProviderKey
from dotenv import dotenv_values

PROJECT_ROOT: Final = Path(__file__).resolve().parents[4]
DEFAULT_RUNTIME_ENV: Final = PROJECT_ROOT / ".local-runtime/provider-startup.env"


@dataclass(frozen=True, slots=True)
class LocalOperator:
    provider: ProviderKey
    profile: str
    service: str


@dataclass(frozen=True, slots=True)
class ProviderStartupDecision:
    provider: ProviderKey
    ready: bool
    reason: str


@dataclass(frozen=True, slots=True)
class ProviderStartupPlan:
    compose_profiles: tuple[str, ...]
    disabled_local_services: tuple[str, ...]
    operator_base_urls: dict[str, str]
    default_access_policies: dict[str, str]
    canary_targets: tuple[dict[str, object], ...]
    decisions: tuple[ProviderStartupDecision, ...]

    def environment(self) -> dict[str, str]:
        return {
            "COMPOSE_PROFILES": ",".join(self.compose_profiles),
            "RUNNER_OPERATOR_BASE_URLS": _json(self.operator_base_urls),
            "RUNNER_DEFAULT_ACCESS_POLICIES": _json(self.default_access_policies),
            "PROVIDER_CANARY_TARGETS": _json(list(self.canary_targets)),
        }


_LOCAL_OPERATORS: Final = {
    item.provider: item
    for item in (
        LocalOperator(
            ProviderKey.YOUTUBE,
            "youtube-operator",
            "youtube-operator-runner",
        ),
        LocalOperator(ProviderKey.DOUYIN, "douyin-operator", "douyin-operator-runner"),
        LocalOperator(ProviderKey.REDDIT, "reddit-operator", "reddit-operator-runner"),
        LocalOperator(
            ProviderKey.WECHAT_CHANNELS,
            "wechat-channels-operator",
            "wechat-channels-operator-runner",
        ),
        LocalOperator(ProviderKey.YOUKU, "youku-operator", "youku-operator-runner"),
        LocalOperator(
            ProviderKey.QQVIDEO,
            "qqvideo-operator",
            "qqvideo-operator-runner",
        ),
    )
}


def build_startup_plan(
    values: Mapping[str, str],
) -> ProviderStartupPlan:
    """Resolve deployment intent without sampling transient Cookie health."""
    profiles = _profiles(values.get("COMPOSE_PROFILES", ""))
    operator_urls = _string_mapping(values.get("RUNNER_OPERATOR_BASE_URLS", "{}"))
    policies = _string_mapping(values.get("RUNNER_DEFAULT_ACCESS_POLICIES", "{}"))
    targets = _targets(values.get("PROVIDER_CANARY_TARGETS", "[]"))
    decisions: list[ProviderStartupDecision] = []
    for provider, local in _LOCAL_OPERATORS.items():
        endpoint = operator_urls.get(provider.value)
        if endpoint is not None and _is_local_endpoint(endpoint, local.service):
            profiles.add(local.profile)
            decisions.append(
                ProviderStartupDecision(provider, False, "source_checked_at_runtime")
            )
        elif local.profile in profiles:
            if endpoint is None:
                raise ValueError(
                    f"{provider.value}: enabled operator needs an endpoint"
                )
            # A remote route owns its own runtime, not a duplicate local Runner.
            profiles.remove(local.profile)

    return ProviderStartupPlan(
        compose_profiles=tuple(sorted(profiles)),
        disabled_local_services=tuple(
            sorted(
                local.service
                for local in _LOCAL_OPERATORS.values()
                if local.profile not in profiles
            )
        ),
        operator_base_urls=dict(sorted(operator_urls.items())),
        default_access_policies=dict(sorted(policies.items())),
        canary_targets=tuple(targets),
        decisions=tuple(sorted(decisions, key=lambda item: item.provider.value)),
    )


def load_environment(env_file: Path) -> dict[str, str]:
    if not env_file.is_file():
        raise FileNotFoundError(env_file)
    loaded = {
        key: value
        for key, value in dotenv_values(env_file).items()
        if value is not None
    }
    for key in (
        "COMPOSE_PROFILES",
        "RUNNER_OPERATOR_BASE_URLS",
        "RUNNER_DEFAULT_ACCESS_POLICIES",
        "PROVIDER_CANARY_TARGETS",
        "PROVIDER_SOURCE_ENCRYPTION_KEY",
    ):
        if key in os.environ:
            loaded[key] = os.environ[key]
    return loaded


def write_runtime_environment(target: Path, plan: ProviderStartupPlan) -> None:
    target = target.absolute()
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(target.parent, 0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=".provider-startup-", dir=target.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            os.fchmod(output.fileno(), 0o600)
            for key, value in plan.environment().items():
                output.write(f"{key}={value}\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, target)
        os.chmod(target, 0o600)
    finally:
        temporary.unlink(missing_ok=True)


def _is_local_endpoint(endpoint: str, service: str) -> bool:
    return urlsplit(endpoint).hostname == service


def _profiles(value: str) -> set[str]:
    return {item.strip() for item in value.split(",") if item.strip()}


def _string_mapping(value: str) -> dict[str, str]:
    try:
        document = json.loads(value)
    except json.JSONDecodeError:
        raise ValueError("provider startup mapping is invalid") from None
    if not isinstance(document, dict) or not all(
        isinstance(key, str) and isinstance(item, str) for key, item in document.items()
    ):
        raise ValueError("provider startup mapping is invalid")
    return dict(document)


def _targets(value: str) -> list[dict[str, object]]:
    try:
        document = json.loads(value)
    except json.JSONDecodeError:
        raise ValueError("provider canary targets are invalid") from None
    if not isinstance(document, list) or not all(
        isinstance(item, dict) for item in document
    ):
        raise ValueError("provider canary targets are invalid")
    return [dict(item) for item in document]


def _json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def _print_plan(plan: ProviderStartupPlan) -> None:
    for decision in plan.decisions:
        state = "operator-configured"
        print(f"provider {decision.provider.value}: {state} ({decision.reason})")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="保留已配置 Provider 路线并启动自动来源恢复"
    )
    parser.add_argument("command", choices=("prepare", "start"))
    parser.add_argument("--env-file", type=Path, default=PROJECT_ROOT / ".env")
    parser.add_argument(
        "--compose-file", type=Path, default=PROJECT_ROOT / "docker-compose.yml"
    )
    parser.add_argument("--runtime-env", type=Path, default=DEFAULT_RUNTIME_ENV)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    env_file = args.env_file.absolute()
    compose_file = args.compose_file.absolute()
    values = load_environment(env_file)
    plan = build_startup_plan(values)
    file_routes = {"youtube", "douyin", "reddit", "youku", "qqvideo"}
    if any(
        item.provider.value in file_routes for item in plan.decisions
    ) and not values.get("PROVIDER_SOURCE_ENCRYPTION_KEY"):
        raise SystemExit(
            "已配置托管文件路线；请先配置稳定的 PROVIDER_SOURCE_ENCRYPTION_KEY，"
            "并按 008 手册登记来源。启动不会删除路线或生成替代密钥。"
        )
    write_runtime_environment(args.runtime_env, plan)
    _print_plan(plan)
    if args.command == "prepare":
        return 0
    environment = os.environ.copy()
    environment.update(plan.environment())
    compose = (
        "docker",
        "compose",
        "--env-file",
        str(env_file),
        "--env-file",
        str(args.runtime_env.absolute()),
        "-f",
        str(compose_file),
    )
    configured_services = frozenset(
        subprocess.run(
            (*compose, "config", "--services"),
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )
    disabled_services = tuple(
        service
        for service in plan.disabled_local_services
        if service in configured_services
    )
    if disabled_services:
        subprocess.run(
            (
                *compose,
                "rm",
                "--stop",
                "--force",
                *disabled_services,
            ),
            cwd=PROJECT_ROOT,
            env=environment,
            check=True,
        )
    command = (
        *compose,
        "up",
        "-d",
        "--build",
        "--force-recreate",
        "--remove-orphans",
        "--wait",
        "--wait-timeout",
        "300",
    )
    subprocess.run(command, cwd=PROJECT_ROOT, env=environment, check=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
