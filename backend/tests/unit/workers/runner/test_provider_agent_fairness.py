from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from threading import Event, Lock

import pytest
from app.services.provider_types import ProviderKey
from app.workers.runner import provider_cookie_agent as agent
from app.workers.runner.provider_cookie_queue import ProviderCookieOperation


def test_slow_refresh_does_not_block_probes_while_authorization_waits(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    slow_started, probe_served, release = Event(), Event(), Event()
    counts: dict[ProviderKey, int] = {}
    lock = Lock()

    def authorize(*_args: object, **_kwargs: object) -> None:
        release.wait(3)

    def drain(
        _root: Path,
        provider: ProviderKey,
        *_args: object,
        operation: ProviderCookieOperation,
        **_kwargs: object,
    ) -> None:
        if operation is ProviderCookieOperation.PROBE:
            if provider is ProviderKey.YOUTUBE and slow_started.is_set():
                probe_served.set()
            return
        with lock:
            counts[provider] = counts.get(provider, 0) + 1
            attempt = counts[provider]
        if provider is ProviderKey.DOUYIN and attempt >= 2:
            slow_started.set()
            release.wait(3)

    monkeypatch.setattr(
        agent,
        "browser_session_providers",
        lambda: frozenset({ProviderKey.DOUYIN, ProviderKey.YOUTUBE}),
    )
    monkeypatch.setattr(agent, "drain_authorization_requests", authorize)
    monkeypatch.setattr(agent, "drain_request_batch", drain)
    # termination_guard installs signals and belongs to the main thread.
    monkeypatch.setattr(agent, "termination_guard", nullcontext)
    with ThreadPoolExecutor(max_workers=1) as executor:
        running = executor.submit(agent.drain_requests, tmp_path, profile="Default")
        try:
            assert slow_started.wait(1), "second refresh never started"
            assert probe_served.wait(0.3), "a slow platform blocked another probe"
        finally:
            release.set()
        running.result(timeout=2)
