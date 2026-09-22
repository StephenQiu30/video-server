"""Only first-party visitor material may enter a short read-only guest lease."""

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from app.services.provider_guest import GuestScope
from app.services.provider_types import ProviderKey
from app.workers.runner._secure_file import (
    atomic_write_bytes,
    no_follow_flag,
    validate_private_file,
)
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.netscape_cookie import live_cookie_payload

_PREFIX = b"# FrameFetch guest lease: "
_MAX_BYTES = 64 * 1024


def validate_guest_material(
    scope: GuestScope, payload: bytes, *, now: datetime
) -> bytes:
    # A positive list cannot admit an account Cookie accidentally supplied by an
    # operator source or a future extractor. Expand only with a verified recipe.
    if scope.provider is not ProviderKey.DOUYIN or len(payload) > _MAX_BYTES:
        raise RunnerFailure("guest_context_required", status=503)
    live, names = live_cookie_payload(
        payload, frozenset({"iesdouyin.com", "douyin.com"}), now=now.timestamp()
    )
    if names != {"ttwid"}:
        raise RunnerFailure("guest_context_required", status=503)
    # Reject even empty/unexpired account entries, not merely the names returned
    # by live_cookie_payload (which intentionally ignores empty values).
    from app.workers.runner.netscape_cookie import parse_cookie_payload

    if any(
        cookie.name != "ttwid"
        for cookie in parse_cookie_payload(
            payload, frozenset({"iesdouyin.com", "douyin.com"})
        )
    ):
        raise RunnerFailure("guest_context_required", status=503)
    return live


@dataclass(frozen=True, slots=True)
class GuestFileLease:
    revision: int
    payload: bytes = field(repr=False)

    @property
    def version(self) -> str:
        return f"guest-{self.revision}"


def publish_guest_lease(
    path: Path,
    scope: GuestScope,
    revision: int,
    payload: bytes,
    *,
    now: datetime,
    deadline: datetime,
) -> None:
    if revision < 1 or not 0 < (deadline - now).total_seconds() <= 90:
        raise ValueError("invalid guest lease deadline")
    live = validate_guest_material(scope, payload, now=now)
    header, body = live.split(b"\n", 1)
    lease = _PREFIX + f"{scope.key} {revision} {int(deadline.timestamp())}\n".encode()
    atomic_write_bytes(path, header + b"\n" + lease + body)


def read_guest_lease(path: Path, scope: GuestScope, *, now: datetime) -> GuestFileLease:
    try:
        fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK | no_follow_flag())
        with os.fdopen(fd, "rb") as source:
            validate_private_file(source.fileno(), "unsafe guest lease")
            payload = source.read(_MAX_BYTES + 1)
        if len(payload) > _MAX_BYTES:
            raise ValueError("guest lease too large")
        headers = [line for line in payload.splitlines() if line.startswith(_PREFIX)]
        if len(headers) != 1:
            raise ValueError("missing guest lease")
        key, revision, deadline = (
            headers[0].removeprefix(_PREFIX).decode("ascii").split()
        )
        if (
            key != scope.key
            or int(revision) < 1
            or not now.timestamp() < int(deadline) <= now.timestamp() + 90
        ):
            raise ValueError("invalid guest lease")
        # Renewal timestamps are not part of the operation's credential identity.
        material = (
            b"\n".join(
                line for line in payload.splitlines() if not line.startswith(_PREFIX)
            )
            + b"\n"
        )
        return GuestFileLease(
            int(revision), validate_guest_material(scope, material, now=now)
        )
    except (OSError, ValueError, UnicodeError, RunnerFailure):
        raise RunnerFailure("guest_context_required", status=503) from None
