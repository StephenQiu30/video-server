"""Install and inspect the cross-platform per-user analysis Agent.

Run from the backend directory:
    python -m app.workers.analysis.agent_cli install
"""

from __future__ import annotations

import argparse
import asyncio
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

from app.application.analysis_execution import AnalysisArtifactError
from app.core.config import REPOSITORY_ROOT, Settings
from app.infrastructure.object_storage import StoredObjectStat
from app.workers.analysis.agent_platforms import (
    agent_paths,
    agent_status,
    install_agent,
    uninstall_agent,
)
from app.workers.analysis.main import build_runtime

ANALYSIS_STORAGE_PROBE = "system/analysis-readiness-v1"


class StorageProbe(Protocol):
    async def stat(self, object_key: str) -> StoredObjectStat | None: ...


def main() -> None:
    parser = argparse.ArgumentParser(description="帧取 AI 分析 Agent 管理工具")
    parser.add_argument(
        "command", choices=("run", "install", "uninstall", "status", "doctor")
    )
    parser.add_argument(
        "--env-file",
        type=Path,
        help="Agent 使用的环境文件；默认读取仓库根目录 .env",
    )
    args = parser.parse_args()
    if args.command == "run":
        from app.workers.analysis.main import main as run_worker

        try:
            run_worker(_settings(_env_file(args.env_file)))
        except Exception as exc:
            _record_agent_failure(exc, agent_paths().stderr)
            raise
        return
    if args.command == "doctor":
        asyncio.run(_doctor(_settings(_env_file(args.env_file))))
        return
    if args.command == "install":
        install_agent(_env_file(args.env_file))
        return
    if args.command == "uninstall":
        uninstall_agent()
        return
    raise SystemExit(agent_status())


def _env_file(value: Path | None) -> Path:
    candidate = value or REPOSITORY_ROOT / ".env"
    if not candidate.is_absolute():
        candidate = Path.cwd() / candidate
    resolved = candidate.expanduser().resolve()
    if not resolved.is_file():
        raise SystemExit(f"environment file is unavailable: {resolved}")
    return resolved


def _settings(env_file: Path) -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=env_file,
        service_role="analysis-worker",
    )


async def _doctor(settings: Settings) -> None:
    runtime = build_runtime(settings)
    try:
        selection = await runtime.resolver.resolve()
        try:
            await runtime.loader.prepare_root()
        except AnalysisArtifactError as exc:
            if exc.code == "analysis_sandbox_unavailable":
                raise SystemExit(
                    "not ready: analysis workspace must be outside directories "
                    "governed by AGENTS.md"
                ) from None
            raise
        await _verify_storage(runtime.storage)
        print(
            f"ready: provider={selection.provider} model={selection.model} "
            f"runtime={selection.cli_version} storage=ready"
        )
    finally:
        await runtime.engine.dispose()


async def _verify_storage(storage: StorageProbe) -> None:
    try:
        probe = await storage.stat(ANALYSIS_STORAGE_PROBE)
    except Exception:
        raise SystemExit(
            "not ready: analysis MinIO credentials cannot read the readiness probe"
        ) from None
    if probe is None or probe.size_bytes <= 0:
        raise SystemExit("not ready: analysis MinIO readiness probe is missing")


def _record_agent_failure(error: Exception, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    frames = traceback.extract_tb(error.__traceback__)
    with target.open("a", encoding="utf-8") as stream:
        stream.write(
            f"{datetime.now(UTC).isoformat()} analysis agent exited: "
            f"{type(error).__name__}\n"
        )
        for frame in frames:
            stream.write(f"  {frame.filename}:{frame.lineno} in {frame.name}\n")


if __name__ == "__main__":
    main()
