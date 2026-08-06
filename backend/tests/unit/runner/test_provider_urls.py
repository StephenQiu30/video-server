from app.runner.provider_urls import (
    provider_command_args,
    provider_inspection_attempts,
    provider_inspection_retry_delay,
    provider_request_url,
)


def test_uses_public_vimeo_player_endpoint_for_canonical_video() -> None:
    assert (
        provider_request_url("https://vimeo.com/76979871?share=copy")
        == "https://player.vimeo.com/video/76979871"
    )
    assert (
        provider_request_url("https://www.vimeo.com/76979871/")
        == "https://player.vimeo.com/video/76979871"
    )


def test_preserves_unlisted_and_non_vimeo_urls() -> None:
    assert (
        provider_request_url("https://vimeo.com/76979871/private-hash")
        == "https://vimeo.com/76979871/private-hash"
    )
    assert (
        provider_request_url("https://media.example.com/76979871")
        == "https://media.example.com/76979871"
    )


def test_targets_tiktok_request_impersonation_and_retries() -> None:
    url = "https://www.tiktok.com/@creator/video/123"

    assert provider_command_args(url) == (
        "--impersonate",
        "Chrome-136:Macos-15",
    )
    assert provider_inspection_attempts(url) == 8
    assert provider_inspection_retry_delay(url) == 0.5
    assert provider_command_args("https://vimeo.com/123") == ()
    assert provider_inspection_attempts("https://vimeo.com/123") == 2
    assert provider_inspection_retry_delay("https://vimeo.com/123") == 1
