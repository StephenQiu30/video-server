"""Normal first-party visitor initialization; no account source or challenge solving."""

import asyncio
from datetime import datetime, timedelta

import httpx

from app.services.provider_guest import GuestScope
from app.services.provider_types import ProviderKey
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.guest_material import validate_guest_material
from app.workers.runner.netscape_cookie import is_allowed_domain, serialize_cookies


class PublicGuestBootstrap:
    def __init__(
        self, proxy: str, *, transport: httpx.AsyncBaseTransport | None = None
    ) -> None:
        self._proxy = proxy
        self._transport = transport

    async def prepare(
        self, scope: GuestScope, *, now: datetime
    ) -> tuple[bytes, datetime]:
        if scope.provider is not ProviderKey.DOUYIN:
            raise RunnerFailure("provider_configuration_missing", status=503)
        try:
            # New, empty cookie jar every time. Neither redirects nor user URLs
            # select a destination. The same controlled egress is used by Runner.
            async with (
                asyncio.timeout(15),
                httpx.AsyncClient(
                    proxy=self._proxy if self._transport is None else None,
                    transport=self._transport,
                    trust_env=False,
                    follow_redirects=False,
                    timeout=15,
                ) as client,
            ):
                async with client.stream(
                    "GET", "https://www.iesdouyin.com/"
                ) as response:
                    if response.status_code == 429:
                        raise RunnerFailure("provider_rate_limited", status=429)
                    if response.status_code in {401, 403}:
                        raise RunnerFailure(
                            "provider_verification_required", status=422
                        )
                    if response.status_code not in {200, 301, 302}:
                        raise RunnerFailure(
                            "provider_temporarily_unavailable", status=503
                        )
                    size = 0
                    async for chunk in response.aiter_bytes():
                        size += len(chunk)
                        if size > 1024**2:
                            raise RunnerFailure(
                                "provider_temporarily_unavailable", status=503
                            )
                cookies = [
                    cookie
                    for cookie in client.cookies.jar
                    if cookie.name == "ttwid"
                    and is_allowed_domain(
                        cookie.domain, {"iesdouyin.com", "douyin.com"}
                    )
                    and cookie.value
                ]
                payload = validate_guest_material(
                    scope, serialize_cookies(cookies), now=now
                )
                expiry = min(
                    [
                        now + timedelta(minutes=15),
                        *(
                            datetime.fromtimestamp(cookie.expires, tz=now.tzinfo)
                            for cookie in cookies
                            if cookie.expires
                        ),
                    ]
                )
                if expiry <= now:
                    raise RunnerFailure("guest_context_required", status=503)
                return payload, expiry
        except (httpx.HTTPError, TimeoutError):
            raise RunnerFailure(
                "provider_temporarily_unavailable", status=503
            ) from None
