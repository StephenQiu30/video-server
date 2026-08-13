"""Install and inspect the cross-platform per-user analysis Agent.

Run from the backend directory:
    python -m app.workers.analysis.agent_cli install
"""

from __future__ import annotations

import argparse
import asyncio
from typing import Protocol

from app.core.config import get_settings_for_role
from app.infrastructure.object_storage import StoredObjectStat
from app.workers.analysis.agent_platforms import (
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
    args = parser.parse_args()
    if args.command == "run":
        from app.workers.analysis.main import main as run_worker

        run_worker()
        return
    if args.command == "doctor":
        asyncio.run(_doctor())
        return
    if args.command == "install":
        install_agent()
        return
    if args.command == "uninstall":
        uninstall_agent()
        return
    raise SystemExit(agent_status())


async def _doctor() -> None:
    runtime = build_runtime(get_settings_for_role("analysis-worker"))
    try:
        selection = await runtime.resolver.resolve()
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


if __name__ == "__main__":
    main()
