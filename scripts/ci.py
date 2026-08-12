#!/usr/bin/env python3
"""Run the repository quality gates through one local and CI entry point."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ACTION_USE_PATTERN = re.compile(r"^\s*-\s+uses:\s+([^\s#]+)", re.MULTILINE)
PINNED_REF_PATTERN = re.compile(r"^[0-9a-f]{40}$")


def run(label: str, *command: str, cwd: Path = ROOT) -> None:
    print(f"\n==> {label}", flush=True)
    environment = os.environ.copy()
    environment.setdefault("CI", "true")
    subprocess.run(command, cwd=cwd, env=environment, check=True)


def unpinned_actions(contents: str) -> list[str]:
    """Return remote workflow action references that are not commit pinned."""
    invalid: list[str] = []
    for reference in ACTION_USE_PATTERN.findall(contents):
        if reference.startswith(("./", "docker://")):
            continue
        _, separator, revision = reference.rpartition("@")
        if not separator or PINNED_REF_PATTERN.fullmatch(revision) is None:
            invalid.append(reference)
    return invalid


def check_workflow_action_pins() -> None:
    invalid: list[str] = []
    for workflow in sorted((ROOT / ".github" / "workflows").glob("*.y*ml")):
        for reference in unpinned_actions(workflow.read_text(encoding="utf-8")):
            invalid.append(f"{workflow.relative_to(ROOT)}: {reference}")
    if invalid:
        details = "\n  - ".join(invalid)
        raise RuntimeError(f"GitHub Actions 必须固定到完整提交 SHA：\n  - {details}")


def repository() -> None:
    run(
        "提交规范测试",
        "python3",
        "-m",
        "unittest",
        "discover",
        "-s",
        "scripts/tests",
        "-v",
    )
    print("\n==> GitHub Actions 固定版本检查", flush=True)
    check_workflow_action_pins()
    run("Git 工作区空白错误检查", "git", "diff", "--check")
    with tempfile.TemporaryDirectory(prefix="video-server-ci-") as directory:
        temporary = Path(directory)
        development_env = temporary / ".env"
        production_env = temporary / ".env.prod"
        shutil.copyfile(ROOT / ".env.example", development_env)
        shutil.copyfile(ROOT / ".env.prod.example", production_env)
        run(
            "开发 Compose 配置",
            "docker",
            "compose",
            "--env-file",
            str(development_env),
            "-f",
            "docker-compose.yml",
            "config",
            "--quiet",
        )
        run(
            "生产 Compose 配置",
            "docker",
            "compose",
            "--env-file",
            str(production_env),
            "-f",
            "docker-compose.yml",
            "-f",
            "docker-compose-prod.yml",
            "config",
            "--quiet",
        )


def backend(*, quick: bool = False) -> None:
    if not quick:
        run("后端锁定依赖", "uv", "sync", "--frozen", "--dev", cwd=ROOT / "backend")
    run(
        "后端 Ruff",
        "uv",
        "run",
        "--frozen",
        "ruff",
        "check",
        "app",
        "tests",
        cwd=ROOT / "backend",
    )
    run(
        "后端格式",
        "uv",
        "run",
        "--frozen",
        "ruff",
        "format",
        "--check",
        "app",
        "tests",
        cwd=ROOT / "backend",
    )
    if quick:
        return
    run(
        "后端严格类型",
        "uv",
        "run",
        "--frozen",
        "mypy",
        "--strict",
        "app",
        cwd=ROOT / "backend",
    )
    run("后端测试", "uv", "run", "--frozen", "pytest", "-q", cwd=ROOT / "backend")


def frontend(*, quick: bool = False) -> None:
    if not quick:
        run("前端锁定依赖", "npm", "ci", cwd=ROOT / "frontend")
        run(
            "前端生产依赖审计",
            "npm",
            "audit",
            "--omit=dev",
            "--audit-level=high",
            cwd=ROOT / "frontend",
        )
    run("前端 lint 与类型", "npm", "run", "lint", cwd=ROOT / "frontend")
    run("前端格式", "npm", "run", "format:check", cwd=ROOT / "frontend")
    if quick:
        return
    run("前端测试", "npm", "test", cwd=ROOT / "frontend")
    run("前端生产构建", "npm", "run", "build", cwd=ROOT / "frontend")


def staged_files() -> tuple[str, ...]:
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return tuple(result.stdout.splitlines())


def pre_commit() -> None:
    run("暂存区空白错误检查", "git", "diff", "--cached", "--check")
    repository()
    files = staged_files()
    if any(path.startswith("backend/") for path in files):
        backend(quick=True)
    if any(path.startswith("frontend/") for path in files):
        frontend(quick=True)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "stage",
        choices=("repository", "backend", "frontend", "pre-commit", "pre-push", "all"),
    )
    stage = parser.parse_args().stage
    if stage == "repository":
        repository()
    elif stage == "backend":
        backend()
    elif stage == "frontend":
        frontend()
    elif stage == "pre-commit":
        pre_commit()
    else:
        repository()
        backend()
        frontend()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
