from __future__ import annotations

import asyncio
import os
import stat
from pathlib import Path

import pytest
from app.domain.providers import ProviderKey, ProviderSessionVersion
from app.runner.errors import RunnerFailure
from app.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
    seal_cookie_lease,
)
from app.runner.provider_cookie_queue import AGENT_READY_PAYLOAD, ProviderCookieRequest
from app.runner.provider_cookie_sync import ProviderCookieSyncClient
from cryptography.hazmat.primitives.asymmetric.x25519 import X25519PrivateKey

TOKEN = "1" * 32
PRIVATE_KEY = b"p" * 32
COOKIE = b"# Netscape HTTP Cookie File\n.youtube.com\tTRUE\t/\tTRUE\t0\tSID\tx\n"


def bridge_root(tmp_path: Path) -> Path:
    root = tmp_path / "bridge"
    (root / "requests").mkdir(parents=True)
    (root / "responses").mkdir()
    (root / ".agent-installed").write_bytes(AGENT_READY_PAYLOAD)
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


def write_lease_response(
    root: Path,
    request: Path,
    lease: ProviderCookieLease,
) -> None:
    requested = ProviderCookieRequest.parse(request.read_bytes())
    write_response(
        root,
        seal_cookie_lease(
            lease,
            requested.public_key,
            associated_data=requested.serialize(),
        ),
    )


def client(
    root: Path,
    *,
    timeout_seconds: float = 20,
    poll_interval_seconds: float = 0.05,
) -> ProviderCookieSyncClient:
    return ProviderCookieSyncClient(
        root,
        timeout_seconds=timeout_seconds,
        poll_interval_seconds=poll_interval_seconds,
        token_factory=lambda: TOKEN,
        private_key_factory=lambda: X25519PrivateKey.from_private_bytes(PRIVATE_KEY),
    )


async def test_sync_uses_typed_0600_request_and_cleans_files(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    sync_client = client(root, poll_interval_seconds=0.001)

    task = asyncio.create_task(
        sync_client.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    )
    request = await wait_for_request(root)
    requested = ProviderCookieRequest.parse(request.read_bytes())
    assert requested.provider is ProviderKey.YOUTUBE
    assert requested.version is ProviderSessionVersion.BROWSER
    if os.name == "posix":
        assert stat.S_IMODE(request.stat().st_mode) == 0o600
    write_lease_response(
        root,
        request,
        ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE),
    )
    assert await task == COOKIE

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
    sync_client = client(root, poll_interval_seconds=0.001)

    task = asyncio.create_task(
        sync_client.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    )
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
    sync_client = client(
        root,
        timeout_seconds=0.01,
        poll_interval_seconds=0.001,
    )

    with pytest.raises(RunnerFailure) as caught:
        await sync_client.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)

    assert caught.value.code == "provider_session_unavailable"
    assert list((root / "requests").iterdir()) == []


async def test_sync_rejects_symlink_directories_without_writing(tmp_path: Path) -> None:
    target = bridge_root(tmp_path)
    linked = tmp_path / "linked"
    linked.symlink_to(target, target_is_directory=True)
    sync_client = client(linked)

    assert (
        sync_client.is_ready(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
        is False
    )
    with pytest.raises(RunnerFailure) as caught:
        await sync_client.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    assert caught.value.code == "provider_session_unavailable"
    assert list((target / "requests").iterdir()) == []


async def test_sync_rejects_symlink_queue_directory(tmp_path: Path) -> None:
    root = tmp_path / "bridge"
    target = tmp_path / "untrusted-requests"
    target.mkdir()
    root.mkdir()
    (root / "requests").symlink_to(target, target_is_directory=True)
    (root / "responses").mkdir()
    sync_client = client(root)

    assert (
        sync_client.is_ready(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
        is False
    )
    with pytest.raises(RunnerFailure) as caught:
        await sync_client.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    assert caught.value.code == "provider_session_unavailable"
    assert list(target.iterdir()) == []


async def test_sync_rejects_symlink_response(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    sync_client = client(root, poll_interval_seconds=0.001)
    target = tmp_path / "untrusted"
    target.write_bytes(b"ok")

    task = asyncio.create_task(
        sync_client.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
    )
    await wait_for_request(root)
    (root / "responses" / f"{TOKEN}.response").symlink_to(target)

    with pytest.raises(RunnerFailure) as caught:
        await task
    assert caught.value.code == "provider_session_unavailable"
    assert list((root / "responses").iterdir()) == []


def test_readiness_only_validates_bridge_directories(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    sync_client = client(root)

    assert (
        sync_client.is_ready(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
        is True
    )
    assert list((root / "requests").iterdir()) == []
    assert list((root / "responses").iterdir()) == []


def test_readiness_requires_the_installed_agent_marker(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    (root / ".agent-installed").unlink()
    sync_client = client(root)

    assert (
        sync_client.is_ready(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
        is False
    )


@pytest.mark.skipif(not getattr(os, "O_PATH", 0), reason="Linux O_PATH behavior")
async def test_sync_needs_no_directory_read_permission(tmp_path: Path) -> None:
    root = bridge_root(tmp_path)
    requests = root / "requests"
    responses = root / "responses"
    os.chmod(root, 0o111)
    os.chmod(requests, 0o333)
    os.chmod(responses, 0o111)
    sync_client = client(root, poll_interval_seconds=0.001)

    try:
        task = asyncio.create_task(
            sync_client.sync(ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER)
        )
        request = await wait_for_request(root)
        os.chmod(responses, 0o311)
        write_lease_response(
            root,
            request,
            ProviderCookieLease(ProviderCookieLeaseStatus.OK, COOKIE),
        )
        os.chmod(responses, 0o111)
        assert await task == COOKIE

        assert not request.exists()
        assert (responses / f"{TOKEN}.response").exists()
    finally:
        os.chmod(root, 0o700)
        os.chmod(requests, 0o700)
        os.chmod(responses, 0o700)
