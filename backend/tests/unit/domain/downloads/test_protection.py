from app.domain.downloads import (
    ProtectionState,
    classify_dash_manifest,
    classify_hls_manifest,
)


def test_clear_hls_manifest_is_classified_without_fetching_keys() -> None:
    result = classify_hls_manifest(b"#EXTM3U\n#EXTINF:10,\nsegment-1.ts\n")

    assert result.state is ProtectionState.CLEAR
    assert result.reason is None


def test_hls_encryption_and_drm_are_rejected_from_manifest_only() -> None:
    encrypted = classify_hls_manifest(
        b'#EXTM3U\n#EXT-X-KEY:METHOD=AES-128,URI="https://key.invalid/1"\n'
    )
    drm = classify_hls_manifest(
        b'#EXTM3U\n#EXT-X-SESSION-KEY:METHOD=SAMPLE-AES,URI="skd://asset"\n'
    )

    assert encrypted.state is ProtectionState.ENCRYPTED
    assert encrypted.reason == "hls_encrypted"
    assert drm.state is ProtectionState.DRM
    assert drm.reason == "hls_drm"


def test_unknown_hls_key_method_fails_closed() -> None:
    result = classify_hls_manifest(b"#EXTM3U\n#EXT-X-KEY:METHOD=VENDOR-X\n")

    assert result.state is ProtectionState.UNKNOWN
    assert result.reason == "hls_key_method_unknown"


def test_dash_is_never_downloadable_and_drm_is_distinguished() -> None:
    clear = classify_dash_manifest(b'<MPD xmlns="urn:mpeg:dash:schema:mpd:2011"/>')
    protected = classify_dash_manifest(
        b'<MPD><Period><ContentProtection schemeIdUri="urn:uuid:test"/></Period></MPD>'
    )

    assert clear.state is ProtectionState.UNKNOWN
    assert clear.reason == "dash_download_not_enabled"
    assert protected.state is ProtectionState.DRM
    assert protected.reason == "dash_drm"
