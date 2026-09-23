"""Preserve declared Provider routes across temporary source outages."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import stat
import subprocess
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Final
from urllib.parse import urlsplit

from app.services.provider_types import ProviderKey
from app.workers.runner._secure_file import (
    ensure_private_directory,
    no_follow_flag,
    validate_private_file,
)
from app.workers.runner.provider_source_host import (
    install_launch_agent,
    load_settings,
    sync_once,
)
from cryptography.fernet import Fernet
from dotenv import dotenv_values

PROJECT_ROOT: Final = Path(__file__).resolve().parents[4]
DEFAULT_RUNTIME_ENV: Final = PROJECT_ROOT / ".local-runtime/provider-startup.env"
DEFAULT_SOURCE_KEY: Final = PROJECT_ROOT / ".local-runtime/provider-source.key"
_AUTO_BROWSER_PROVIDERS: Final = frozenset(
    {ProviderKey.YOUTUBE, ProviderKey.DOUYIN, ProviderKey.REDDIT}
)


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
    *,
    auto_browser_routes: frozenset[ProviderKey] = frozenset(),
) -> ProviderStartupPlan:
    """Resolve deployment intent without sampling transient Cookie health."""
    profiles = _profiles(values.get("COMPOSE_PROFILES", ""))
    operator_urls = _string_mapping(values.get("RUNNER_OPERATOR_BASE_URLS", "{}"))
    policies = _string_mapping(values.get("RUNNER_DEFAULT_ACCESS_POLICIES", "{}"))
    targets = _targets(values.get("PROVIDER_CANARY_TARGETS", "[]"))
    for provider in auto_browser_routes:
        if provider not in _AUTO_BROWSER_PROVIDERS:
            raise ValueError("browser source provider is not admitted")
        local = _LOCAL_OPERATORS[provider]
        existing = operator_urls.get(provider.value)
        if existing is not None and not _is_local_endpoint(existing, local.service):
            raise ValueError("browser source needs its local operator endpoint")
        operator_urls.setdefault(provider.value, f"http://{local.service}:19100")
        policies.setdefault(provider.value, "operator_public")
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
        "AUTO_BROWSER_SOURCE_PROVIDERS",
    ):
        if key in os.environ:
            loaded[key] = os.environ[key]
    return loaded


def write_runtime_environment(
    target: Path, plan: ProviderStartupPlan, *, source_key: str | None = None
) -> None:
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
            if source_key is not None:
                output.write(f"PROVIDER_SOURCE_ENCRYPTION_KEY={source_key}\n")
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


def _auto_providers(value: str) -> tuple[ProviderKey, ...]:
    result: list[ProviderKey] = []
    for raw in value.split(","):
        if not raw.strip():
            continue
        provider = ProviderKey(raw.strip())
        if provider not in _AUTO_BROWSER_PROVIDERS:
            raise ValueError("browser source provider is not admitted")
        if provider not in result:
            result.append(provider)
    return tuple(result)


def _source_key(values: Mapping[str, str], path: Path = DEFAULT_SOURCE_KEY) -> str:
    configured = values.get("PROVIDER_SOURCE_ENCRYPTION_KEY", "")
    if configured:
        Fernet(configured.encode("ascii"))
        return configured
    ensure_private_directory(path.parent)
    try:
        descriptor = os.open(path, os.O_RDONLY | no_follow_flag())
    except FileNotFoundError:
        key = Fernet.generate_key()
        try:
            descriptor = os.open(
                path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | no_follow_flag(), 0o600
            )
        except FileExistsError:
            descriptor = os.open(path, os.O_RDONLY | no_follow_flag())
        else:
            with os.fdopen(descriptor, "wb") as output:
                output.write(key + b"\n")
                output.flush()
                os.fsync(output.fileno())
            return key.decode("ascii")
    with os.fdopen(descriptor, "rb") as source:
        validate_private_file(source.fileno(), "unsafe provider source key")
        if stat.S_IMODE(os.fstat(source.fileno()).st_mode) != 0o600:
            raise OSError("unsafe provider source key")
        raw = source.read(256).strip()
    Fernet(raw)
    return raw.decode("ascii")


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
    default_auto = "youtube" if sys.platform == "darwin" else ""
    requested_auto = values.get("AUTO_BROWSER_SOURCE_PROVIDERS")
    auto_providers = _auto_providers(
        default_auto if requested_auto is None else requested_auto
    )
    if requested_auto is None:
        declared_urls = _string_mapping(values.get("RUNNER_OPERATOR_BASE_URLS", "{}"))
        auto_providers = tuple(
            provider
            for provider in auto_providers
            if provider.value not in declared_urls
            or _is_local_endpoint(
                declared_urls[provider.value], _LOCAL_OPERATORS[provider].service
            )
        )
    if auto_providers and sys.platform != "darwin":
        raise SystemExit("此宿主系统尚无已验收的浏览器来源适配器")
    source_key: str | None = None
    if auto_providers:
        source_key = _source_key(values)
        values["PROVIDER_SOURCE_ENCRYPTION_KEY"] = source_key
    plan = build_startup_plan(values, auto_browser_routes=frozenset(auto_providers))
    file_routes = {"youtube", "douyin", "reddit", "youku", "qqvideo"}
    if any(
        item.provider.value in file_routes for item in plan.decisions
    ) and not values.get("PROVIDER_SOURCE_ENCRYPTION_KEY"):
        raise SystemExit(
            "已配置托管文件路线；请先配置稳定的 PROVIDER_SOURCE_ENCRYPTION_KEY，"
            "并按 008 手册登记来源。启动不会删除路线或生成替代密钥。"
        )
    write_runtime_environment(args.runtime_env, plan, source_key=source_key)
    _print_plan(plan)
    if args.command == "prepare":
        return 0
    if auto_providers:
        settings = load_settings(env_file, args.runtime_env)
        for provider in auto_providers:
            try:
                status = asyncio.run(sync_once(provider, settings))
            except Exception:
                status = "source_sync_unavailable"
            print(f"provider {provider.value}: {status}")
    environment = os.environ.copy()
    environment.update(plan.environment())
    if source_key is not None:
        environment["PROVIDER_SOURCE_ENCRYPTION_KEY"] = source_key
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
    if auto_providers:
        install_launch_agent(
            env_file=env_file,
            runtime_env=args.runtime_env,
            providers=auto_providers,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
