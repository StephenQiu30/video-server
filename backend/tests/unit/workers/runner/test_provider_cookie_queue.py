from __future__ import annotations

from pathlib import Path

import pytest
from app.services.provider_types import ProviderKey, ProviderSessionVersion
from app.workers.runner.provider_cookie_lease import (
    ProviderCookieLease,
    ProviderCookieLeaseStatus,
)
from app.workers.runner.provider_cookie_queue import (
    ProviderCookieOperation,
    ProviderCookieRequest,
    drain_request_batch,
    prepare_runtime,
)

PUBLIC_KEY = b"k" * 32


@pytest.mark.parametrize(
    "payload",
    [
        b"probe:tiktok\nbrowser\na2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2s\n",
        b"probe:probe:youtube\nbrowser\na2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2s\n",
        b"probe:youtube\nunknown\na2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2tra2s\n",
    ],
)
def test_probe_rejects_unknown_or_unallowlisted_identity(payload: bytes) -> None:
    with pytest.raises(ValueError):
        ProviderCookieRequest.parse(payload)


def _request(path: Path, provider: ProviderKey) -> None:
    path.write_bytes(
        ProviderCookieRequest(
            provider,
            ProviderSessionVersion.BROWSER,
            PUBLIC_KEY,
        ).serialize()
    )


def test_queue_batches_only_identical_typed_provider_requests(tmp_path: Path) -> None:
    requests, responses = prepare_runtime(tmp_path)
    _request(requests / f"{'0' * 32}.request", ProviderKey.YOUTUBE)
    _request(requests / f"{'1' * 32}.request", ProviderKey.YOUTUBE)
    calls: list[tuple[ProviderKey, ProviderSessionVersion]] = []
    published: dict[str, ProviderCookieLease] = {}

    def refresh(
        provider: ProviderKey, version: ProviderSessionVersion
    ) -> ProviderCookieLease:
        calls.append((provider, version))
        return ProviderCookieLease(ProviderCookieLeaseStatus.OK, b"cookie")

    def publish(
        target: Path,
        request: ProviderCookieRequest,
        result: ProviderCookieLease,
    ) -> None:
        assert request.public_key == PUBLIC_KEY
        published[target.name] = result
        target.write_bytes(b"encrypted")

    drain_request_batch(
        tmp_path,
        ProviderKey.YOUTUBE,
        refresh,
        publish,
        acknowledgement_timeout_seconds=0,
    )

    assert calls == [
        (ProviderKey.YOUTUBE, ProviderSessionVersion.BROWSER),
    ]
    assert published == {
        f"{'0' * 32}.response": ProviderCookieLease(
            ProviderCookieLeaseStatus.OK, b"cookie"
        ),
        f"{'1' * 32}.response": ProviderCookieLease(
            ProviderCookieLeaseStatus.OK, b"cookie"
        ),
    }
    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


def test_queue_removes_untyped_or_unallowlisted_requests(tmp_path: Path) -> None:
    requests, responses = prepare_runtime(tmp_path)
    invalid = (
        b"",
        b"youtube\nunknown\na2tra2tra2tra2tra2tra2tra2tra2tra2tra2s\n",
        b"tiktok\nbrowser\na2tra2tra2tra2tra2tra2tra2tra2tra2tra2s\n",
        b"youtube\nbrowser\ninvalid\n",
        b"youtube\nbrowser\na2tra2tra2tra2tra2tra2tra2tra2tra2tra2s\ntrailing",
    )
    for index, payload in enumerate(invalid):
        (requests / f"{index:032x}.request").write_bytes(payload)

    calls: list[object] = []
    drain_request_batch(
        tmp_path,
        ProviderKey.YOUTUBE,
        lambda *args: (
            calls.append(args)
            or ProviderCookieLease(ProviderCookieLeaseStatus.OK, b"cookie")
        ),
        lambda *args: calls.append(args),
        acknowledgement_timeout_seconds=0,
    )

    assert calls == []
    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())


@pytest.mark.parametrize("operation", list(ProviderCookieOperation))
def test_queue_rejects_a_request_for_another_provider(
    tmp_path: Path, operation: ProviderCookieOperation
) -> None:
    requests, responses = prepare_runtime(tmp_path)
    (requests / f"{'3' * 32}.request").write_bytes(
        ProviderCookieRequest(
            ProviderKey.INSTAGRAM, ProviderSessionVersion.BROWSER, PUBLIC_KEY, operation
        ).serialize()
    )
    calls: list[object] = []

    drain_request_batch(
        tmp_path,
        ProviderKey.YOUTUBE,
        lambda *args: (
            calls.append(args)
            or ProviderCookieLease(ProviderCookieLeaseStatus.OK, b"cookie")
        ),
        lambda *args: calls.append(args),
        acknowledgement_timeout_seconds=0,
    )

    assert calls == []
    assert not tuple(requests.iterdir())
    assert not tuple(responses.iterdir())
