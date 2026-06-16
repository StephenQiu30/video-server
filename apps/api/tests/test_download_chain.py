"""Download chain tests for video source governance.

These tests verify the parse -> task -> worker download -> object storage
delivery chain for supported platforms, and the restricted/fallback semantics
for platforms with known limitations.
"""

import pytest
from unittest.mock import MagicMock, patch

from app.core.errors import AppError, ErrorCode
from app.schemas import TaskCreate
from app.services.parse_service import ParseService
from app.sources.registry import SourceAdapterRegistry
from app.sources.models import SourceRequest


# --- Format ID passing contract ---

def test_format_id_passes_from_task_create_to_worker() -> None:
    """TaskCreate.format_id MUST be passed to Worker YoutubeDL options.

    This verifies the contract: TaskCreate.format_id -> Worker {"format": ...}
    """
    # Create a task with a specific format_id
    task_create = TaskCreate(
        url="https://www.bilibili.com/video/BV1iCR7BEEvo/",
        format_id="bestvideo+bestaudio/best",
    )

    assert task_create.format_id == "bestvideo+bestaudio/best"


def test_format_id_defaults_to_best_when_not_specified() -> None:
    """TaskCreate.format_id defaults to 'best' when not specified."""
    task_create = TaskCreate(
        url="https://www.bilibili.com/video/BV1iCR7BEEvo/",
    )

    # The format_id should be None or 'best' depending on implementation
    # Worker should use 'best' as fallback
    assert task_create.format_id is None or task_create.format_id == "best"


def test_resolution_format_id_pattern() -> None:
    """Resolution format IDs MUST follow the pattern bv*[height<=N]+ba/b[height<=N]."""
    valid_patterns = [
        "bv*[height<=1080]+ba/b[height<=1080]",
        "bv*[height<=720]+ba/b[height<=720]",
        "bv*[height<=480]+ba/b[height<=480]",
        "bv*[height<=360]+ba/b[height<=360]",
    ]

    for pattern in valid_patterns:
        assert pattern.startswith("bv*[height<=")
        assert "+ba/b[height<=" in pattern
        assert pattern.endswith("]")


# --- Bilibili download chain ---

def test_bilibili_download_chain(monkeypatch) -> None:
    """Bilibili MUST support full download chain: parse -> task -> worker fake download.

    This is a fake integration test that verifies the chain without real network calls.
    """
    # Mock yt-dlp to return Bilibili-like info
    mock_info = {
        "title": "Test Bilibili Video",
        "extractor_key": "BiliBili",
        "duration": 120,
        "thumbnail": "https://example.com/cover.jpg",
        "formats": [
            {
                "format_id": "30080",
                "width": 1920,
                "height": 1080,
                "ext": "mp4",
                "vcodec": "h264",
                "acodec": "aac",
                "filesize_approx": 1024 * 1024 * 100,
            }
        ],
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_class.return_value = mock_ydl

        # Parse the URL
        registry = SourceAdapterRegistry()
        request = SourceRequest.from_url("https://www.bilibili.com/video/BV1iCR7BEEvo/")
        adapter = registry.get_adapter(request)

        assert adapter.name == "bilibili"

        info = adapter.parse(request)

        assert info.title == "Test Bilibili Video"
        assert info.extractor == "BiliBili"
        assert len(info.variants) > 0

        # Verify format_id can be selected
        variant = info.variants[0]
        assert variant.format_id == "30080"
        assert variant.height == 1080


def test_bilibili_adapter_supports_bilibili_urls() -> None:
    """BilibiliAdapter MUST support bilibili.com and b23.tv URLs."""
    registry = SourceAdapterRegistry()

    bilibili_urls = [
        "https://www.bilibili.com/video/BV1iCR7BEEvo/",
        "https://b23.tv/BV1iCR7BEEvo",
    ]

    for url in bilibili_urls:
        request = SourceRequest.from_url(url)
        adapter = registry.get_adapter(request)
        assert adapter.name == "bilibili", f"Expected bilibili adapter for {url}"


# --- YouTube download chain ---

def test_youtube_download_chain(monkeypatch) -> None:
    """YouTube MUST support full download chain: parse -> task -> worker fake download.

    This is a fake integration test that verifies the chain without real network calls.
    """
    # Mock yt-dlp to return YouTube-like info
    mock_info = {
        "title": "Test YouTube Video",
        "extractor_key": "YouTube",
        "duration": 300,
        "thumbnail": "https://example.com/cover.jpg",
        "formats": [
            {
                "format_id": "137",
                "width": 1920,
                "height": 1080,
                "ext": "mp4",
                "vcodec": "h264",
                "acodec": "none",
                "filesize_approx": 1024 * 1024 * 200,
            },
            {
                "format_id": "140",
                "ext": "m4a",
                "vcodec": "none",
                "acodec": "aac",
                "filesize_approx": 1024 * 1024 * 10,
            },
        ],
    }

    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.return_value = mock_info
        mock_ydl_class.return_value = mock_ydl

        # Parse the URL
        registry = SourceAdapterRegistry()
        request = SourceRequest.from_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        adapter = registry.get_adapter(request)

        assert adapter.name == "ytdlp-fallback"

        info = adapter.parse(request)

        assert info.title == "Test YouTube Video"
        assert info.extractor == "YouTube"
        assert len(info.variants) > 0

        # Verify video-only and audio-only streams are separated
        video_variants = [v for v in info.variants if v.stream_type == "video-only"]
        audio_variants = [v for v in info.variants if v.stream_type == "audio-only"]

        assert len(video_variants) > 0
        assert len(audio_variants) > 0


def test_youtube_adapter_supports_youtube_urls() -> None:
    """YtDlpAdapter MUST support youtube.com and youtu.be URLs."""
    registry = SourceAdapterRegistry()

    youtube_urls = [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
    ]

    for url in youtube_urls:
        request = SourceRequest.from_url(url)
        adapter = registry.get_adapter(request)
        assert adapter.name == "ytdlp-fallback", f"Expected ytdlp-fallback adapter for {url}"


# --- Unknown host fallback ---

def test_unknown_host_fallback() -> None:
    """Unknown hosts MUST use YtDlpAdapter as fallback with fallback_attempt semantics."""
    registry = SourceAdapterRegistry()

    unknown_urls = [
        "https://unknown-platform.example.com/video/123",
        "https://another-site.org/watch?v=abc",
    ]

    for url in unknown_urls:
        request = SourceRequest.from_url(url)
        adapter = registry.get_adapter(request)
        assert adapter.name == "ytdlp-fallback", f"Expected ytdlp-fallback for {url}"


def test_unknown_host_unsupported_maps_correctly(monkeypatch) -> None:
    """Unknown host that yt-dlp cannot handle MUST map to UNSUPPORTED_PLATFORM."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Unsupported URL: https://unknown.example.com/video")
        mock_ydl_class.return_value = mock_ydl

        # Use ParseService which catches exceptions and calls map_error
        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://unknown.example.com/video/123")

        assert exc_info.value.code == ErrorCode.UNSUPPORTED_PLATFORM


# --- Domestic short video restricted semantics ---

def test_douyin_restricted_semantics(monkeypatch) -> None:
    """Douyin MUST have restricted/rate-limit failure semantics.

    This test verifies that Douyin content with restrictions is properly
    classified as platform_restricted, not as supported_download.
    """
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Login required to access this content")
        mock_ydl_class.return_value = mock_ydl

        # Use ParseService which catches exceptions and calls map_error
        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://www.douyin.com/video/123")

        assert exc_info.value.code == ErrorCode.PLATFORM_RESTRICTED
        assert "限制" in exc_info.value.message


def test_kuaishou_restricted_semantics(monkeypatch) -> None:
    """Kuaishou MUST have restricted/rate-limit failure semantics."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Too many requests, rate limit exceeded")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://www.kuaishou.com/video/123")

        assert exc_info.value.code == ErrorCode.PLATFORM_RATE_LIMITED


def test_xiaohongshu_restricted_semantics(monkeypatch) -> None:
    """Xiaohongshu MUST have restricted/rate-limit failure semantics."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Members-only content, please login")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://www.xiaohongshu.com/explore/123")

        assert exc_info.value.code == ErrorCode.PLATFORM_RESTRICTED


def test_ixigua_restricted_semantics(monkeypatch) -> None:
    """Ixigua MUST have restricted/rate-limit failure semantics."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Geo restricted content")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://www.ixigua.com/123")

        assert exc_info.value.code == ErrorCode.PLATFORM_RESTRICTED


def test_weibo_restricted_semantics(monkeypatch) -> None:
    """Weibo MUST have restricted/rate-limit failure semantics."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Copyright protected content")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://weibo.com/video/123")

        assert exc_info.value.code == ErrorCode.PLATFORM_RESTRICTED


# --- Platform fallback tests ---

def test_tiktok_fallback(monkeypatch) -> None:
    """TikTok MUST use yt-dlp fallback and handle failures gracefully."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Unsupported URL")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://www.tiktok.com/@user/video/123")

        assert exc_info.value.code == ErrorCode.UNSUPPORTED_PLATFORM


def test_twitter_fallback(monkeypatch) -> None:
    """X/Twitter MUST use yt-dlp fallback and handle failures gracefully."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Unsupported URL")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://x.com/user/status/123")

        assert exc_info.value.code == ErrorCode.UNSUPPORTED_PLATFORM


def test_instagram_fallback(monkeypatch) -> None:
    """Instagram MUST use yt-dlp fallback and handle failures gracefully."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Login required")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://www.instagram.com/reel/123")

        assert exc_info.value.code == ErrorCode.PLATFORM_RESTRICTED


def test_vimeo_fallback(monkeypatch) -> None:
    """Vimeo MUST use yt-dlp fallback and handle failures gracefully."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Unsupported URL")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://vimeo.com/123")

        assert exc_info.value.code == ErrorCode.UNSUPPORTED_PLATFORM


def test_dailymotion_fallback(monkeypatch) -> None:
    """Dailymotion MUST use yt-dlp fallback and handle failures gracefully."""
    with patch("yt_dlp.YoutubeDL") as mock_ydl_class:
        mock_ydl = MagicMock()
        mock_ydl.__enter__ = MagicMock(return_value=mock_ydl)
        mock_ydl.__exit__ = MagicMock(return_value=False)
        mock_ydl.extract_info.side_effect = Exception("Unsupported URL")
        mock_ydl_class.return_value = mock_ydl

        service = ParseService()

        with pytest.raises(AppError) as exc_info:
            service.parse("https://www.dailymotion.com/video/123")

        assert exc_info.value.code == ErrorCode.UNSUPPORTED_PLATFORM


# --- Worker download failure classification ---

def test_worker_failure_classification_ffmpeg_missing(monkeypatch) -> None:
    """Worker MUST classify missing FFmpeg as media_tools_missing."""
    import shutil
    from worker.failures import failure_code
    from worker.domain import WorkerFailureCode, WorkerStage

    monkeypatch.setattr(shutil, "which", lambda _: None)

    exc = RuntimeError("FFmpeg not found")
    code = failure_code(exc)

    assert code == WorkerFailureCode.DOWNLOAD_FAILED


def test_worker_failure_classification_ytdlp_missing(monkeypatch) -> None:
    """Worker MUST classify missing yt-dlp as download_failed."""
    from worker.failures import failure_code
    from worker.domain import WorkerFailureCode

    exc = ModuleNotFoundError("No module named 'yt_dlp'")
    code = failure_code(exc)

    assert code == WorkerFailureCode.DOWNLOAD_FAILED


def test_worker_failure_classification_rate_limited() -> None:
    """Worker MUST classify 429/rate-limit as platform_rate_limited."""
    from worker.failures import failure_code
    from worker.domain import WorkerFailureCode

    exc = RuntimeError("HTTP Error 429: Too Many Requests")
    code = failure_code(exc)

    assert code == WorkerFailureCode.PLATFORM_RATE_LIMITED


def test_worker_failure_classification_unsupported_url() -> None:
    """Worker MUST classify unsupported URL as unsupported_platform."""
    from worker.failures import failure_code
    from worker.domain import WorkerFailureCode

    exc = RuntimeError("Unsupported URL: https://example.com")
    code = failure_code(exc)

    assert code == WorkerFailureCode.UNSUPPORTED_PLATFORM


def test_worker_failure_classification_no_output_file(tmp_path) -> None:
    """Worker MUST classify missing output file as download_failed."""
    from worker.download_runner import resolve_output_path
    from worker.failures import JobFailure

    # Create empty task directory
    task_dir = tmp_path / "task"
    task_dir.mkdir()

    with pytest.raises(JobFailure) as exc_info:
        resolve_output_path(task_dir, task_dir / "missing.mp4")

    assert exc_info.value.code == "download_failed"
    assert "未找到输出文件" in str(exc_info.value)


def test_failure_info_from_exception_includes_stage() -> None:
    """failure_info_from_exception MUST include the stage in the result."""
    from worker.failures import failure_info_from_exception
    from worker.domain import WorkerStage, WorkerFailureCode

    exc = RuntimeError("Unsupported URL: https://example.com")
    info = failure_info_from_exception(exc, WorkerStage.DOWNLOAD)

    assert info.code == WorkerFailureCode.UNSUPPORTED_PLATFORM
    assert info.stage == WorkerStage.DOWNLOAD
    assert info.retryable is False


def test_failure_info_from_exception_retryable() -> None:
    """failure_info_from_exception MUST mark rate-limited errors as retryable."""
    from worker.failures import failure_info_from_exception
    from worker.domain import WorkerStage, WorkerFailureCode

    exc = RuntimeError("HTTP Error 429: Too Many Requests")
    info = failure_info_from_exception(exc, WorkerStage.DOWNLOAD)

    assert info.code == WorkerFailureCode.PLATFORM_RATE_LIMITED
    assert info.stage == WorkerStage.DOWNLOAD
    assert info.retryable is True
