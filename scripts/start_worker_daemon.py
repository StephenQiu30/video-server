#!/usr/bin/env python3
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 4:
        print("Usage: start_worker_daemon.py ROOT_DIR PID_FILE LOG_FILE", file=sys.stderr)
        return 2

    root_dir = Path(sys.argv[1])
    pid_file = Path(sys.argv[2])
    log_file = Path(sys.argv[3])
    log_file.parent.mkdir(parents=True, exist_ok=True)

    env = os.environ.copy()
    env["PYTHONPATH"] = f"{env.get('PYTHONPATH', '')}:apps/api:apps/worker:packages/shared"
    env.setdefault("RQ_WORKER_MODE", "simple")

    with log_file.open("ab", buffering=0) as log:
        process = subprocess.Popen(
            ["./scripts/dev_worker.sh"],
            cwd=root_dir,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            close_fds=True,
            start_new_session=True,
        )

    pid_file.write_text(str(process.pid), encoding="utf-8")
    print(process.pid)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
