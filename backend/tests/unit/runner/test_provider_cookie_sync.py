from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path

import pytest
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_sync import ProviderCookieSyncClient

TOKEN = "1" * 32


def bridge_root(tmp_path: Path) -> Path:
    root = tmp_path / "bridge"
    (root / "requests").mkdir(parents=True)
    (root / "responses").mkdir()
    (root / ".agent-installed").write_text("installed\n")
    return root


async def wait_for_request(root: Path) -> Path:
    request = root / "requests" / f"{TOKEN}.request"
    async with asyncio.timeout(1):
        while not request.exists():
            await asyncio.sleep(0.001)
    return request


def write_response(root: Path, payload: bytes) -> None:
    response = root / "responses" / f"{TOKEN}.response"
    pending = response.with_suffix(".pending")
    pending.write_bytes(payload)
    os.replace(pending, response)


async def test_sync_uses_empty_0600_request_and_cleans_files(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    client = ProviderCookieSyncClient(
        root,
        poll_interval_seconds=0.001,
        token_factory=lambda: TOKEN,
    )

    task = asyncio.create_task(client.sync())
    request = await wait_for_request(root)
    assert request.read_bytes() == b""
    if os.name == "posix":
        assert stat.S_IMODE(request.stat().st_mode) == 0o600
    write_response(root, b"ok")
    await task

    assert list((root / "requests").iterdir()) == []
    assert list((root / "responses").iterdir()) == []


@pytest.mark.parametrize(
    ("response", "expected_code", "expected_status"),
    [
        (b"credential_required", "credential_required", 422),
        (b"provider_session_unavailable", "provider_session_unavailable", 503),
        (b"ok\n", "provider_session_unavailable", 503),
        (b"unknown", "provider_session_unavailable", 503),
    ],
)
async def test_sync_maps_only_strict_stable_responses(
    tmp_path: Path,
    response: bytes,
    expected_code: str,
    expected_status: int,
) -> None:
    root = bridge_root(tmp_path)
    client = ProviderCookieSyncClient(
        root,
        poll_interval_seconds=0.001,
        token_factory=lambda: TOKEN,
    )

    task = asyncio.create_task(client.sync())
    await wait_for_request(root)
    write_response(root, response)

    with pytest.raises(RunnerFailure) as caught:
        await task
    assert caught.value.code == expected_code
    assert caught.value.status == expected_status
    assert list((root / "requests").iterdir()) == []
    assert list((root / "responses").iterdir()) == []


async def test_sync_timeout_is_bounded_and_cleans_request(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    client = ProviderCookieSyncClient(
        root,
        timeout_seconds=0.01,
        poll_interval_seconds=0.001,
        token_factory=lambda: TOKEN,
    )

    with pytest.raises(RunnerFailure) as caught:
        await client.sync()

    assert caught.value.code == "provider_session_unavailable"
    assert list((root / "requests").iterdir()) == []


async def test_sync_rejects_symlink_directories_without_writing(tmp_path: Path) -> None:
    target = bridge_root(tmp_path)
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    client = ProviderCookieSyncClient(linked, token_factory=lambda: TOKEN)

    assert client.is_ready() is False
    with pytest.raises(RunnerFailure) as caught:
        await client.sync()
    assert caught.value.code == "provider_session_unavailable"
    assert list((target / "requests").iterdir()) == []


async def test_sync_rejects_symlink_queue_directory(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    target = tmp_path / "untrusted-requests"
    target.mkdir()
    root.mkdir()
    (root / "requests").symlink_to(target, target_is_directory=True)
    (root / "responses").mkdir()
    client = ProviderCookieSyncClient(root, token_factory=lambda: TOKEN)

    assert client.is_ready() is False
    with pytest.raises(RunnerFailure) as caught:
        await client.sync()
    assert caught.value.code == "provider_session_unavailable"
    assert list(target.iterdir()) == []


async def test_sync_rejects_symlink_response(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    client = ProviderCookieSyncClient(
        root,
        poll_interval_seconds=0.001,
        token_factory=lambda: TOKEN,
    )
    target = tmp_path / "untrusted"
    target.write_bytes(b"ok")

    task = asyncio.create_task(client.sync())
    await wait_for_request(root)
    (root / "responses" / f"{TOKEN}.response").symlink_to(target)

    with pytest.raises(RunnerFailure) as caught:
        await task
    assert caught.value.code == "provider_session_unavailable"
    assert list((root / "responses").iterdir()) == []


def test_readiness_only_validates_bridge_directories(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    client = ProviderCookieSyncClient(root)

    assert client.is_ready() is True
    assert list((root / "requests").iterdir()) == []
    assert list((root / "responses").iterdir()) == []


def test_readiness_requires_the_installed_agent_marker(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    (root / ".agent-installed").unlink()
    client = ProviderCookieSyncClient(root)

    assert client.is_ready() is False


@pytest.mark.skipif(not getattr(os, "O_PATH", 0), reason="Linux O_PATH behavior")
async def test_sync_needs_no_directory_read_permission(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    requests = root / "requests"
    responses = root / "responses"
    os.chmod(root, 0o111)
    os.chmod(requests, 0o333)
    os.chmod(responses, 0o111)
    client = ProviderCookieSyncClient(
        root,
        poll_interval_seconds=0.001,
        token_factory=lambda: TOKEN,
    )

    try:
        task = asyncio.create_task(client.sync())
        request = await wait_for_request(root)
        os.chmod(responses, 0o311)
        write_response(root, b"ok")
        os.chmod(responses, 0o111)
        await task

        assert not request.exists()
        assert (responses / f"{TOKEN}.response").exists()
    finally:
        os.chmod(root, 0o700)
        os.chmod(requests, 0o700)
        os.chmod(responses, 0o700)
