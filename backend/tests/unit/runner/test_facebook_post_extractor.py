from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any

import pytest
from app.runner.plugins.yt_dlp_plugins.extractor.facebook_post import FacebookPostIE
from yt_dlp.utils import ExtractorError

SHARE_URL = "https://www.facebook.com/share/p/example/"
POST_ID = "1347155834118247"
POST_URL = f"https://www.facebook.com/groups/claudeaicommunity/permalink/{POST_ID}/"


def facebook_page(*media: dict[str, Any]) -> str:
    payload = {
        "require": [
            {
                "__bbox": {
                    "result": {
                        "data": {
                            "node_v2": {
                                "attachments": [{"media": item} for item in media]
                            }
                        }
                    }
                }
            }
        ]
    }
    return f'<script type="application/json" data-sjs>{json.dumps(payload)}</script>'


def configured_extractor(
    monkeypatch: pytest.MonkeyPatch,
    webpage: str,
    *,
    final_url: str = POST_URL,
) -> FacebookPostIE:
    extractor = FacebookPostIE()
    monkeypatch.setattr(
        extractor,
        "_download_webpage_handle",
        lambda *args, **kwargs: (webpage, SimpleNamespace(url=final_url)),
    )
    return extractor


def test_share_post_delegates_one_video_to_upstream_facebook(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    extractor = configured_extractor(
        monkeypatch,
        facebook_page({"__typename": "Video", "id": "99887766"}),
    )

    result = extractor._real_extract(SHARE_URL)

    assert result == {
        "_type": "url",
        "url": "facebook:99887766",
        "ie_key": "Facebook",
        "id": "99887766",
    }


@pytest.mark.parametrize(
    "media",
    [
        ({"__typename": "Photo", "id": "10168534459259466"},),
        (
            {"__typename": "Video", "id": "99887766"},
            {"__typename": "Photo", "id": "10168534459259466"},
        ),
    ],
)
def test_rejects_image_and_multi_asset_posts(
    monkeypatch: pytest.MonkeyPatch,
    media: tuple[dict[str, str], ...],
) -> None:
    extractor = configured_extractor(monkeypatch, facebook_page(*media))

    with pytest.raises(ExtractorError, match="image and multi-asset posts"):
        extractor._real_extract(SHARE_URL)


def test_rejects_cross_origin_and_identity_changing_redirects(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = facebook_page({"__typename": "Video", "id": "99887766"})
    with pytest.raises(ExtractorError, match="sharing link unavailable"):
        configured_extractor(
            monkeypatch,
            page,
            final_url=f"https://media.example/groups/example/posts/{POST_ID}/",
        )._real_extract(SHARE_URL)

    with pytest.raises(ExtractorError, match="sharing link unavailable"):
        configured_extractor(
            monkeypatch,
            page,
            final_url=(
                "https://www.facebook.com/groups/claudeaicommunity/posts/other/"
            ),
        )._real_extract(POST_URL)


def test_schema_change_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    extractor = configured_extractor(monkeypatch, "<html>changed</html>")

    with pytest.raises(ExtractorError, match="media structure"):
        extractor._real_extract(SHARE_URL)
