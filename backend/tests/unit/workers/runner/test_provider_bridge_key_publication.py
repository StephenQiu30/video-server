import os
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from app.workers.runner.provider_browser_bridge_store import ProviderBrowserBridgeStore


def test_initial_key_is_never_visible_with_incomplete_contents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    store = ProviderBrowserBridgeStore(tmp_path)
    original_open = os.open
    exposed_sizes: list[int] = []

    def observe_open(path, flags, mode=0o777, *, dir_fd=None):
        fd = original_open(path, flags, mode, dir_fd=dir_fd)
        if Path(path).name == ".key" and flags & os.O_CREAT:
            exposed_sizes.append((tmp_path / "bridge/.key").stat().st_size)
        return fd

    monkeypatch.setattr(os, "open", observe_open)
    store.prepare()

    assert 0 not in exposed_sizes, "another host can read a partially written key"
    assert len((tmp_path / "bridge/.key").read_bytes()) == 32


def test_concurrent_native_hosts_share_one_complete_key(tmp_path: Path) -> None:
    stores = [ProviderBrowserBridgeStore(tmp_path) for _ in range(32)]
    with ThreadPoolExecutor(max_workers=16) as executor:
        list(executor.map(lambda store: store.prepare(), stores))
    key = (tmp_path / "bridge/.key").read_bytes()
    stores[0].prepare()
    assert (tmp_path / "bridge/.key").read_bytes() == key
    assert len(key) == 32
