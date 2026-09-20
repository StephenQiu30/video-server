"""Explicit deployment-side setup of independent, single-provider file sources."""

from __future__ import annotations

import argparse
import fcntl
import os
import stat
import tempfile
from pathlib import Path

from app.services.provider_types import ProviderKey
from app.workers.runner._secure_file import no_follow_flag
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.provider_cookie_boundary import (
    export_provider_cookie_lease_bounded,
)
from app.workers.runner.provider_cookie_file import ProviderCookieFile
from app.workers.runner.provider_cookie_lease import ProviderCookieLeaseStatus
from app.workers.runner.provider_cookie_process import termination_guard
from app.workers.runner.provider_session_bundle import (
    create_backup_key,
    decrypt_session_bundle,
    encrypt_session_bundle,
)
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
        os.O_CREAT | os.O_RDWR | no_follow_flag() | os.O_NONBLOCK,
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
        description="采集、校验或加密迁移单平台会话文件"
    )
    parser.add_argument(
        "command",
        choices=(
            "capture-chrome",
            "import",
            "check",
            "create-backup-key",
            "backup",
            "restore",
        ),
    )
    parser.add_argument(
        "--provider",
        choices=sorted(str(p) for p in session_providers()),
        default="youtube",
    )
    parser.add_argument("--directory", type=Path)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--key-file", type=Path)
    parser.add_argument("--profile", default="Default")
    args = parser.parse_args()
    provider = ProviderKey(args.provider)
    if args.command == "create-backup-key":
        if args.key_file is None:
            parser.error("create-backup-key requires --key-file")
    else:
        if args.directory is None:
            parser.error(f"{args.command} requires --directory")
        if args.command == "import" and args.source is None:
            parser.error("import requires --source")
        if args.command in {"backup", "restore"} and (
            args.bundle is None or args.key_file is None
        ):
            parser.error(f"{args.command} requires --bundle and --key-file")
    try:
        with termination_guard():
            if args.command == "create-backup-key":
                create_backup_key(args.key_file)
            elif args.command == "check":
                ProviderCookieFile(args.directory / "cookies.txt").read(
                    provider, browser_session_policy(provider).version
                )
            elif args.command == "capture-chrome":
                capture_chrome_session(provider, args.directory, profile=args.profile)
            elif args.command == "import":
                payload = ProviderCookieFile(args.source).read(
                    provider, browser_session_policy(provider).version
                )
                publish_session(provider, args.directory, payload)
            elif args.command == "backup":
                payload = ProviderCookieFile(args.directory / "cookies.txt").read(
                    provider, browser_session_policy(provider).version
                )
                encrypt_session_bundle(
                    provider,
                    payload,
                    key_file=args.key_file,
                    destination=args.bundle,
                )
            else:
                payload = decrypt_session_bundle(
                    provider,
                    key_file=args.key_file,
                    source=args.bundle,
                )
                publish_session(provider, args.directory, payload)
    except RunnerFailure as error:
        print(f"单平台来源未就绪：{error.code}")
        return 1
    except OSError:
        print("单平台来源安装未确认：请检查目录权限、占用或磁盘状态。")
        return 1
    if args.command == "create-backup-key":
        print("迁移密钥已创建；请与加密备份分开保管。")
    elif args.command == "backup":
        print("单平台来源已加密备份；密钥未写入备份文件。")
    elif args.command == "restore":
        print("单平台来源已原子恢复；仍需完成真实解析和完整文件验收。")
    else:
        print("单平台来源校验通过；仍需完成真实解析和完整文件验收。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
