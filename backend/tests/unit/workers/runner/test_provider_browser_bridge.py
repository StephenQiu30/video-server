from __future__ import annotations

import json
import struct
import subprocess
import sys
from pathlib import Path

import pytest
from app.services.provider_types import ProviderKey
from app.workers.runner import provider_browser_bridge as bridge
from app.workers.runner.provider_browser_bridge_store import ProviderBrowserBridgeStore

REVISION = "11111111-1111-4111-8111-111111111111"


def _youtube_cookie(value: str = "session") -> dict[str, object]:
    return {
        "domain": ".youtube.com",
        "name": "SID",
        "value": value,
        "path": "/",
        "secure": True,
        "httpOnly": True,
        "expirationDate": None,
    }


def test_sync_message_persists_only_an_encrypted_provider_snapshot(
    tmp_path: Path,
) -> None:
    store = ProviderBrowserBridgeStore(tmp_path)

    result = bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [_youtube_cookie()],
        },
        store,
    )

    assert result == {"ok": True, "provider": "youtube", "revision": REVISION}
    snapshot = tmp_path / "bridge" / "youtube.snapshot"
    assert snapshot.exists()
    assert b"session" not in snapshot.read_bytes()
    assert store.read(ProviderKey.YOUTUBE) is not None


def test_sync_message_rejects_cookie_outside_provider_allowlist(
    tmp_path: Path,
) -> None:
    result = bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [{**_youtube_cookie(), "domain": ".example.com"}],
        },
        ProviderBrowserBridgeStore(tmp_path),
    )

    assert result == {
        "ok": False,
        "error": "invalid_cookies",
        "revision": REVISION,
    }


def test_empty_browser_snapshot_removes_previous_provider_session(
    tmp_path: Path,
) -> None:
    store = ProviderBrowserBridgeStore(tmp_path)
    bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [_youtube_cookie()],
        },
        store,
    )

    result = bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [],
        },
        store,
    )

    assert result == {"ok": True, "provider": "youtube", "revision": REVISION}
    assert store.read(ProviderKey.YOUTUBE) is None


def test_invalid_optional_cookie_does_not_remove_previous_session(
    tmp_path: Path,
) -> None:
    store = ProviderBrowserBridgeStore(tmp_path)
    bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [_youtube_cookie("existing-session")],
        },
        store,
    )

    result = bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [
                _youtube_cookie("replacement-session"),
                {**_youtube_cookie(""), "name": "optional_empty"},
            ],
        },
        store,
    )

    assert result == {"ok": True, "provider": "youtube", "revision": REVISION}
    payload = store.read(ProviderKey.YOUTUBE)
    assert payload is not None
    assert b"replacement-session" in payload


def test_cookie_snapshot_preserves_host_only_domain_and_path_semantics(
    tmp_path: Path,
) -> None:
    store = ProviderBrowserBridgeStore(tmp_path)

    result = bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [
                {
                    **_youtube_cookie("root-domain"),
                    "storeId": "0",
                    "hostOnly": False,
                },
                {
                    **_youtube_cookie("host-path"),
                    "domain": "www.youtube.com",
                    "path": "/studio",
                    "storeId": "0",
                    "hostOnly": True,
                },
            ],
        },
        store,
    )

    assert result["ok"] is True
    payload = store.read(ProviderKey.YOUTUBE)
    assert payload is not None
    assert b".youtube.com\tTRUE\t/\t" in payload
    assert b"www.youtube.com\tFALSE\t/studio\t" in payload


def test_cookie_snapshot_rejects_mixed_browser_stores_without_revoking_previous(
    tmp_path: Path,
) -> None:
    store = ProviderBrowserBridgeStore(tmp_path)
    bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [{**_youtube_cookie("existing-session"), "storeId": "0"}],
        },
        store,
    )

    result = bridge.sync_message(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [
                {**_youtube_cookie("default-store"), "storeId": "0"},
                {
                    **_youtube_cookie("incognito-store"),
                    "name": "HSID",
                    "storeId": "1",
                },
            ],
        },
        store,
    )

    assert result["ok"] is False
    payload = store.read(ProviderKey.YOUTUBE)
    assert payload is not None
    assert b"existing-session" in payload


def test_native_host_install_binds_one_extension_id(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    hosts = tmp_path / "NativeMessagingHosts"
    monkeypatch.setattr(bridge, "CHROME_NATIVE_HOSTS", hosts)
    bridge_home = tmp_path / "browser-bridge"
    monkeypatch.setattr(bridge, "BRIDGE_HOME", bridge_home)
    monkeypatch.setattr(bridge, "NATIVE_HOST_PATH", bridge_home / "host")

    target = bridge.install_native_host(
        tmp_path / "runtime",
        "a" * 32,
        python_executable="/private/venv/bin/python",
    )

    document = json.loads(target.read_text(encoding="utf-8"))
    assert document["allowed_origins"] == ["chrome-extension://" + "a" * 32 + "/"]
    assert document["path"] == str(bridge_home / "host")
    assert "args" not in document
    assert (bridge_home / "host").stat().st_mode & 0o111
    wrapper = (bridge_home / "host").read_text(encoding="utf-8")
    assert "serve --runtime-root" in wrapper
    assert str(tmp_path / "runtime") in wrapper


def test_browser_extension_manifest_has_a_stable_native_host_id() -> None:
    assert bridge.browser_extension_id() == "ljffjbenpehbfgjgdmgecaiimhekoeng"


def test_native_host_rejects_malformed_extension_id(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="extension-id"):
        bridge.install_native_host(tmp_path / "runtime", "not-an-extension-id")


def test_native_host_wrapper_ignores_chrome_origin_and_serves_snapshot(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    bridge_home = tmp_path / "browser-bridge"
    monkeypatch.setattr(bridge, "CHROME_NATIVE_HOSTS", tmp_path / "hosts")
    monkeypatch.setattr(bridge, "BRIDGE_HOME", bridge_home)
    monkeypatch.setattr(bridge, "NATIVE_HOST_PATH", bridge_home / "host")
    runtime = tmp_path / "runtime"
    bridge.install_native_host(runtime, "a" * 32, python_executable=sys.executable)

    payload = json.dumps(
        {
            "type": "sync",
            "provider": "youtube",
            "revision": REVISION,
            "cookies": [_youtube_cookie("wrapper-session")],
        },
        separators=(",", ":"),
    ).encode()
    framed = struct.pack("<I", len(payload)) + payload
    result = subprocess.run(
        [str(bridge_home / "host"), "chrome-extension://" + "a" * 32 + "/"],
        input=framed,
        capture_output=True,
        check=True,
        timeout=5,
    )

    length = struct.unpack("<I", result.stdout[:4])[0]
    assert json.loads(result.stdout[4 : 4 + length]) == {
        "ok": True,
        "provider": "youtube",
        "revision": REVISION,
    }
    assert ProviderBrowserBridgeStore(runtime).read(ProviderKey.YOUTUBE) is not None
