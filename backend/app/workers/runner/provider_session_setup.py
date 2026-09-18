"""Explicit deployment-side setup of independent, single-provider file sources."""

from __future__ import annotations

import argparse
import fcntl
import os
import stat
import tempfile
from pathlib import Path

from app.services.provider_types import ProviderKey
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.provider_cookie_boundary import (
    export_provider_cookie_lease_bounded,
)
from app.workers.runner.provider_cookie_file import ProviderCookieFile
from app.workers.runner.provider_cookie_lease import ProviderCookieLeaseStatus
from app.workers.runner.provider_cookie_process import termination_guard
from app.workers.runner.provider_session_policy import (
    ProviderSessionSource,
    browser_session_policy,
    session_providers,
)


def publish_session(provider: ProviderKey, root: Path, payload: bytes) -> None:
    """Publish only a validated revision; a failed import never replaces the old one."""
    root = root.absolute()
    if any(path.is_symlink() for path in (root, *root.parents)):
        raise OSError("unsafe provider source directory")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    info = root.stat()
    if (
        not stat.S_ISDIR(info.st_mode)
        or info.st_uid != os.getuid()
        or info.st_mode & 0o077
    ):
        raise OSError("provider source must be private to its owner")
    lock = os.open(
        root / ".publish.lock",
        os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
        0o600,
    )
    candidate: Path | None = None
    try:
        info = os.fstat(lock)
        if (
            not stat.S_ISREG(info.st_mode)
            or info.st_uid != os.getuid()
            or info.st_nlink != 1
            or info.st_mode & 0o077
        ):
            raise OSError("unsafe provider source lock")
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fd, name = tempfile.mkstemp(prefix=".cookies-", dir=root)
        candidate = Path(name)
        with os.fdopen(fd, "wb") as output:
            output.write(payload)
            output.flush()
            os.fsync(output.fileno())
        policy = browser_session_policy(provider)
        ProviderCookieFile(candidate).read(provider, policy.version)
        destination = root / "cookies.txt"
        if destination.is_symlink():
            raise OSError("unsafe provider source file")
        os.replace(candidate, destination)
        directory = os.open(root, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if candidate is not None:
            candidate.unlink(missing_ok=True)
        os.close(lock)


def capture_chrome_session(
    provider: ProviderKey, root: Path, *, profile: str = "Default"
) -> None:
    policy = browser_session_policy(provider)
    if policy.source is not ProviderSessionSource.CHROME_PROFILE:
        raise RunnerFailure("provider_session_not_allowed", status=422)
    result = export_provider_cookie_lease_bounded(
        provider=provider,
        profile=profile,
        version=policy.version,
    )
    if result.status is not ProviderCookieLeaseStatus.OK or result.payload is None:
        raise RunnerFailure(result.status.value, status=503)
    publish_session(provider, root, result.payload)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="显式采集已登录 Chrome 或导入单平台会话文件"
    )
    parser.add_argument("command", choices=("capture-chrome", "import", "check"))
    parser.add_argument(
        "--provider",
        choices=sorted(str(p) for p in session_providers()),
        default="youtube",
    )
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--profile", default="Default")
    args = parser.parse_args()
    provider = ProviderKey(args.provider)
    if args.command == "import" and args.source is None:
        parser.error("import requires --source")
    try:
        with termination_guard():
            if args.command == "check":
                ProviderCookieFile(args.directory / "cookies.txt").read(
                    provider, browser_session_policy(provider).version
                )
            elif args.command == "capture-chrome":
                capture_chrome_session(provider, args.directory, profile=args.profile)
            else:
                payload = ProviderCookieFile(args.source).read(
                    provider, browser_session_policy(provider).version
                )
                publish_session(provider, args.directory, payload)
    except RunnerFailure as error:
        print(f"单平台来源未就绪：{error.code}")
        return 1
    except OSError:
        print("单平台来源安装未确认：请检查目录权限、占用或磁盘状态。")
        return 1
    print("单平台来源校验通过；仍需完成真实解析和完整文件验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
