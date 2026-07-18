from __future__ import annotations

import pytest

from video_server.errors import DomainError
from video_server.source.urls import validate_public_addresses


@pytest.mark.security
@pytest.mark.parametrize(
    "address",
    [
        "64:ff9b::7f00:1",
        "64:ff9b::a00:1",
        "::127.0.0.1",
        "::10.0.0.1",
    ],
)
def test_rejects_ipv6_addresses_that_embed_nonpublic_ipv4(address: str) -> None:
    with pytest.raises(DomainError) as error:
        validate_public_addresses([address])

    assert error.value.code == "UNSAFE_URL"
