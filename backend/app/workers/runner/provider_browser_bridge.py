"""Chrome Native Messaging host for the FrameFetch browser connector.

The extension owns access to Chrome's cookie API.  This host is deliberately
small: it validates the provider/domain boundary and stores an encrypted
snapshot for the existing Access Agent.  It never prints or returns Cookie
values and never sends them to the API container.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shlex
import struct
import sys
from collections.abc import Iterator, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.services.provider_types import ProviderAuthorizationSource, ProviderKey
from app.workers.runner._secure_file import atomic_write_bytes, atomic_write_json
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.netscape_cookie import serialize_cookies
from app.workers.runner.provider_authorization_queue import (
    pending_authorization_request,
)
from app.workers.runner.provider_browser_bridge_store import (
    ProviderBrowserBridgeStore,
)
from app.workers.runner.provider_session_policy import (
    ProviderSessionSource,
    browser_session_policy,
    browser_session_providers,
)

HOST_NAME = "com.framefetch.provider.browser"
# Chrome currently caps a native host response at 1 MiB.  Keep the framing
# limit below that boundary so a large Cookie snapshot is rejected before it
# can make the host protocol unusable.
MAX_MESSAGE_BYTES = 1024 * 1024
MAX_COOKIES_PER_PROVIDER = 512
CHROME_NATIVE_HOSTS = (
    Path.home()
    / "Library"
    / "Application Support"
    / "Google"
    / "Chrome"
    / "NativeMessagingHosts"
)
BRIDGE_HOME = (
    Path.home()
    / "Library"
    / "Application Support"
    / "FrameFetch"
    / "provider-browser-bridge"
)
NATIVE_HOST_PATH = BRIDGE_HOME / "provider-browser-bridge"
PROJECT_BACKEND_ROOT = Path(__file__).resolve().parents[3]
BROWSER_EXTENSION_MANIFEST = (
    PROJECT_BACKEND_ROOT.parent / "browser-extension" / "manifest.json"
)


def browser_extension_id(
    manifest_path: Path = BROWSER_EXTENSION_MANIFEST,
) -> str:
    """Derive the stable unpacked-extension ID from its manifest public key."""

    try:
        document = json.loads(manifest_path.read_text(encoding="utf-8"))
        public_key = base64.b64decode(document["key"], validate=True)
    except (FileNotFoundError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        raise OSError("browser extension manifest has no valid public key") from None
    digest = hashlib.sha256(public_key).hexdigest()[:32]
    return "".join(chr(ord("a") + int(character, 16)) for character in digest)


def sync_message(
    message: object,
    store: ProviderBrowserBridgeStore,
    runtime_root: Path,
) -> dict[str, object]:
    """Validate and persist one extension snapshot without exposing secrets."""
    if not isinstance(message, dict) or message.get("type") != "sync":
        return {"ok": False, "error": "invalid_message"}
    try:
        revision = _text(message.get("revision"), max_length=128)
        transaction_id = _text(message.get("transaction_id"), max_length=32)
    except ValueError:
        return {"ok": False, "error": "invalid_message"}
    try:
        provider = ProviderKey(message["provider"])
    except (KeyError, TypeError, ValueError):
        return {
            "ok": False,
            "error": "unsupported_provider",
            "revision": revision,
        }
    if provider not in browser_session_providers():
        return {
            "ok": False,
            "error": "unsupported_provider",
            "revision": revision,
        }
    authorization = pending_authorization_request(runtime_root, transaction_id)
    if (
        authorization is None
        or authorization.provider is not provider
        or authorization.source is not ProviderAuthorizationSource.CURRENT_CHROME
        or authorization.probe
        or datetime.now(UTC) >= authorization.expires_at
    ):
        return {
            "ok": False,
            "error": "authorization_required",
            "revision": revision,
        }
    policy = browser_session_policy(provider)
    if policy.source is not ProviderSessionSource.CHROME_PROFILE:
        return {
            "ok": False,
            "error": "unsupported_provider",
            "revision": revision,
        }
    cookies = message.get("cookies")
    if not isinstance(cookies, list) or len(cookies) > MAX_COOKIES_PER_PROVIDER:
        return {"ok": False, "error": "invalid_cookies", "revision": revision}
    if not cookies:
        try:
            store.remove(provider)
        except OSError:
            return {
                "ok": False,
                "error": "bridge_unavailable",
                "revision": revision,
            }
        return {"ok": True, "provider": provider.value, "revision": revision}
    try:
        payload = serialize_cookies(_cookie_records(cookies, policy.domains))
        store.write(provider, payload)
    except (RunnerFailure, TypeError, ValueError, OSError):
        # A malformed or partial browser update is not proof of logout. Keep
        # the last validated snapshot; only an explicit empty snapshot revokes it.
        return {"ok": False, "error": "invalid_cookies", "revision": revision}
    return {"ok": True, "provider": provider.value, "revision": revision}


def install_native_host(
    runtime_root: Path,
    extension_id: str,
    *,
    python_executable: str | None = None,
) -> Path:
    """Install the one-time Chrome Native Messaging manifest for this host."""
    if not _valid_extension_id(extension_id):
        raise ValueError("extension-id must be a 32-character Chrome extension id")
    if not runtime_root.is_absolute():
        raise ValueError("runtime root must be absolute")
    store = ProviderBrowserBridgeStore(runtime_root)
    store.prepare()
    CHROME_NATIVE_HOSTS.mkdir(mode=0o700, parents=True, exist_ok=True)
    if CHROME_NATIVE_HOSTS.is_symlink():
        raise OSError("unsafe Chrome Native Messaging directory")
    executable = str(Path(python_executable or sys.executable).absolute())
    BRIDGE_HOME.mkdir(mode=0o700, parents=True, exist_ok=True)
    if BRIDGE_HOME.is_symlink():
        raise OSError("unsafe browser bridge directory")
    python_code = (
        "import sys; "
        f"sys.path.insert(0, {str(PROJECT_BACKEND_ROOT)!r}); "
        "from app.workers.runner.provider_browser_bridge import main; "
        "raise SystemExit(main(sys.argv[1:]))"
    )
    # Native Messaging passes the caller origin as argv[1].  The runtime root
    # is deployment state, not an extension-controlled argument, so bind it
    # in this private wrapper instead of relying on unsupported manifest
    # fields such as `args`.
    wrapper = (
        "#!/bin/sh\n"
        f"exec {shlex.quote(executable)} -c {shlex.quote(python_code)} "
        f"serve --runtime-root {shlex.quote(str(runtime_root))}\n"
    ).encode()
    atomic_write_bytes(NATIVE_HOST_PATH, wrapper, mode=0o700)
    if NATIVE_HOST_PATH.is_symlink():
        raise OSError("unsafe browser bridge executable")
    os.chmod(NATIVE_HOST_PATH, 0o700)
    manifest = {
        "name": HOST_NAME,
        "description": "FrameFetch local browser session bridge",
        "path": str(NATIVE_HOST_PATH),
        "type": "stdio",
        "allowed_origins": [f"chrome-extension://{extension_id}/"],
    }
    target = CHROME_NATIVE_HOSTS / f"{HOST_NAME}.json"
    if target.is_symlink():
        raise OSError("unsafe Chrome Native Messaging host manifest")
    atomic_write_json(target, manifest)
    os.chmod(target, 0o600)
    return target


def uninstall_native_host() -> None:
    (CHROME_NATIVE_HOSTS / f"{HOST_NAME}.json").unlink(missing_ok=True)
    NATIVE_HOST_PATH.unlink(missing_ok=True)
    try:
        BRIDGE_HOME.rmdir()
    except OSError:
        pass


def serve(runtime_root: Path) -> int:
    store = ProviderBrowserBridgeStore(runtime_root)
    for message in _messages(sys.stdin.buffer):
        try:
            result = sync_message(message, store, runtime_root)
        except Exception:
            result = {"ok": False, "error": "bridge_unavailable"}
        _write_message(sys.stdout.buffer, result)
    return 0


def _messages(stream: Any) -> Iterator[object]:
    while True:
        header = stream.read(4)
        if not header:
            return
        if len(header) != 4:
            return
        length = struct.unpack("<I", header)[0]
        if not 0 < length <= MAX_MESSAGE_BYTES:
            return
        payload = stream.read(length)
        if len(payload) != length:
            return
        try:
            yield json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            yield None


def _write_message(stream: Any, value: dict[str, object]) -> None:
    payload = json.dumps(value, ensure_ascii=True, separators=(",", ":")).encode(
        "utf-8"
    )
    if len(payload) > MAX_MESSAGE_BYTES:
        payload = b'{"ok":false,"error":"response_too_large"}'
    stream.write(struct.pack("<I", len(payload)))
    stream.write(payload)
    stream.flush()


def _cookie_records(
    cookies: list[object], allowed_domains: tuple[str, ...]
) -> Iterator[Any]:
    from http.cookiejar import Cookie

    snapshot_store_id: str | None = None
    for item in cookies:
        if not isinstance(item, dict):
            raise ValueError("invalid cookie")
        domain = _text(item.get("domain"), max_length=253)
        name = _text(item.get("name"), max_length=256)
        value = _text(item.get("value"), max_length=MAX_MESSAGE_BYTES, allow_empty=True)
        path = _text(item.get("path"), max_length=1024)
        if not domain or not name or not path.startswith("/"):
            raise ValueError("invalid cookie")
        normalized = domain.lstrip(".").casefold()
        if not any(
            normalized == allowed.casefold().lstrip(".")
            or normalized.endswith(f".{allowed.casefold().lstrip('.')}")
            for allowed in allowed_domains
        ):
            raise ValueError("cookie domain is outside the provider allowlist")
        expiration = item.get("expirationDate")
        if expiration is None:
            expires: int | None = None
        elif isinstance(expiration, (float, int)) and expiration >= 0:
            expires = int(expiration)
        else:
            raise ValueError("invalid cookie expiry")
        secure = item.get("secure", False)
        http_only = item.get("httpOnly", False)
        host_only = item.get("hostOnly", not domain.startswith("."))
        store_id = item.get("storeId", "0")
        if (
            not isinstance(secure, bool)
            or not isinstance(http_only, bool)
            or not isinstance(host_only, bool)
            or not isinstance(store_id, str)
            or not store_id
        ):
            raise ValueError("invalid cookie flags")
        if snapshot_store_id is None:
            snapshot_store_id = store_id
        elif snapshot_store_id != store_id:
            raise ValueError("browser stores cannot be mixed in one snapshot")
        yield Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=domain,
            domain_specified=not host_only,
            domain_initial_dot=not host_only and domain.startswith("."),
            path=path,
            path_specified=True,
            secure=secure,
            expires=expires,
            discard=expires is None,
            comment=None,
            comment_url=None,
            rest={"HttpOnly": ""} if http_only else {},
            rfc2109=False,
        )


def _text(value: object, *, max_length: int, allow_empty: bool = False) -> str:
    if (
        not isinstance(value, str)
        or len(value) > max_length
        or (not allow_empty and not value)
    ):
        raise ValueError("invalid text")
    if any(ord(character) < 32 or character in "\t\r\n\x00" for character in value):
        raise ValueError("invalid text")
    return value


def _valid_extension_id(value: str) -> bool:
    return len(value) == 32 and all("a" <= char <= "p" for char in value)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="FrameFetch Chrome browser bridge")
    parser.add_argument("command", choices=("install", "uninstall", "serve"))
    parser.add_argument("--runtime-root", type=Path, default=None)
    parser.add_argument("--extension-id")
    parser.add_argument("--python-executable")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "uninstall":
        uninstall_native_host()
        return 0
    if args.runtime_root is None:
        raise SystemExit("--runtime-root is required")
    if args.command == "install":
        print(
            install_native_host(
                args.runtime_root,
                args.extension_id or browser_extension_id(),
                python_executable=args.python_executable,
            )
        )
        return 0
    return serve(args.runtime_root)


if __name__ == "__main__":
    raise SystemExit(main())
