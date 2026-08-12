#!/usr/bin/env python3
"""Enable the repository-owned Git hooks and commit template."""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure(key: str, value: str) -> None:
    subprocess.run(["git", "config", key, value], cwd=ROOT, check=True)


def main() -> int:
    configure("core.hooksPath", ".githooks")
    configure("commit.template", ".gitmessage")
    print("已启用 .githooks 与 .gitmessage。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
