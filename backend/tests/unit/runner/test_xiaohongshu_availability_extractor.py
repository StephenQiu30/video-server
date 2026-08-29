from __future__ import annotations

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.xiaohongshu_availability import (
    _availability_error,
)


@pytest.mark.parametrize(
    ("error_code", "message"),
    [
        ("300031", "note unavailable"),
        ("300012", "request verification required"),
    ],
)
def test_translates_first_party_error_redirects(
    error_code: str,
    message: str,
) -> None:
    error = _availability_error(
        f"https://www.xiaohongshu.com/404?error_code={error_code}"
    )

    assert error is not None
    assert message in error.casefold()


def test_preserves_successful_first_party_response() -> None:
    assert (
        _availability_error(
            "https://www.xiaohongshu.com/explore/6411cf99000000001300b6d9"
        )
        is None
    )
