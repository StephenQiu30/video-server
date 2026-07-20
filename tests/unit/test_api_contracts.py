from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import Response
from src.api.dependencies import (
    SessionIdentity,
    _state_service,
    get_download_service,
    get_media_service,
    get_or_create_session_identity,
    get_queue_publisher,
    get_readiness_checker,
    get_request_settings,
    maybe_await,
    set_new_session_cookie,
)
from src.api.v1.downloads import (
    _invoke as invoke_download,
)
from src.api.v1.downloads import (
    _job_and_created,
    _translate_repository_error,
    create_download,
    create_download_url,
    get_download,
)
from src.api.v1.media import _invoke as invoke_media
from src.api.v1.media import inspect_media
from src.core.config import Settings
from src.core.errors import AppError
from src.downloads.schemas import CreateDownloadRequest, DownloadUrl
from src.media.schemas import InspectMediaRequest
from src.media.yt_dlp import (
    MediaExtractionError,
    MediaInspectTimeout,
    MediaLimitError,
    UnsupportedMediaError,
)


def settings() -> Settings:
    return Settings(
        database_url="postgresql+asyncpg://video:video@localhost:5432/video",
        rabbitmq_url="amqp://video:video@localhost:5672/",
        minio_endpoint="localhost:9000",
        minio_access_key="video-access",
        minio_secret_key="video-secret",
        minio_bucket="video-artifacts",
        session_secret="a-development-session-secret-with-sufficient-length",
        app_env="test",
    )


def media_result() -> SimpleNamespace:
    format_id = uuid.uuid4()
    return SimpleNamespace(
        id=uuid.uuid4(),
        title="Example title",
        extractor_key="example",
        thumbnail_url=None,
        duration_seconds=12,
        inspect_expires_at=datetime.now(UTC) + timedelta(minutes=5),
        formats=[
            SimpleNamespace(
                id=format_id,
                label="720p",
                width=1280,
                height=720,
                fps=None,
                container="mp4",
                video_codec="avc1",
                audio_codec="mp4a",
                estimated_size_bytes=100,
                requires_merge=False,
            )
        ],
    )


def download_result(status: str = "queued") -> SimpleNamespace:
    now = datetime.now(UTC)
    return SimpleNamespace(
        id=uuid.uuid4(),
        status=status,
        stage=None,
        progress_percent=None,
        downloaded_bytes=None,
        total_bytes=None,
        error_code=None,
        error_message=None,
        artifact=None,
        created_at=now,
        updated_at=now,
    )


@pytest.mark.asyncio
async def test_service_invocation_adapters_cover_method_callable_and_missing() -> None:
    async def method(**kwargs: object) -> str:
        return str(kwargs["value"])

    assert (
        await invoke_media(SimpleNamespace(inspect=method), ("inspect",), value=1)
        == "1"
    )
    assert await invoke_media(lambda **_: "callable", ("missing",)) == "callable"
    assert (
        await invoke_download(
            SimpleNamespace(create_job=method), ("create_job",), value=2
        )
        == "2"
    )
    with pytest.raises(AppError, match="not ready"):
        await invoke_download(SimpleNamespace(), ("missing",))
    assert await maybe_await(3) == 3
    assert await maybe_await(AsyncMock(return_value=4)()) == 4


def test_dependency_state_and_session_cookie_branches() -> None:
    state = SimpleNamespace(media_service="media", download_service="download")
    request = SimpleNamespace(app=SimpleNamespace(state=state))
    assert get_media_service(request) == "media"
    assert get_download_service(request) == "download"
    assert get_queue_publisher(request) is None
    assert get_readiness_checker(request) is None
    state.rabbitmq_publisher = "publisher"
    state.readiness_checker = lambda: True
    assert get_queue_publisher(request) == "publisher"
    assert get_readiness_checker(request) is not None
    assert (
        get_request_settings(
            SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(settings="s")))
        )
        == "s"
    )
    with pytest.raises(AppError):
        _state_service(
            SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace())), ("missing",)
        )

    response = Response()
    identity = SessionIdentity("token", "hash", is_new=True)
    set_new_session_cookie(identity, response, settings())
    assert "video_session=token" in response.headers["set-cookie"]
    # Existing identities must not overwrite their cookie.
    untouched = Response()
    set_new_session_cookie(SessionIdentity("token", "hash"), untouched, settings())
    assert "set-cookie" not in untouched.headers


def test_or_create_identity_uses_existing_or_new_session(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request = SimpleNamespace()
    response = Response()
    cfg = settings()
    monkeypatch.setattr(
        "src.api.dependencies.session_token_from_request", lambda *_: None
    )
    created = get_or_create_session_identity(request, response, cfg)
    assert created.is_new is True
    assert created.token_hash != created.token
    monkeypatch.setattr(
        "src.api.dependencies.session_token_from_request", lambda *_: "existing"
    )
    existing = get_or_create_session_identity(request, response, cfg)
    assert existing.token == "existing" and not existing.is_new


@pytest.mark.asyncio
async def test_media_endpoint_success_and_failure_translation() -> None:
    identity = SessionIdentity("token", "hash", is_new=False)
    payload = InspectMediaRequest(url="https://example.test/video")
    response = Response()
    service = SimpleNamespace(inspect=lambda **_: media_result())
    result = await inspect_media(
        payload, None, response, None, settings(), identity, service
    )
    assert result.title == "Example title"

    for exc, code, status in (
        (MediaInspectTimeout("timeout"), "RESOURCE_LIMIT_EXCEEDED", 422),
        (MediaLimitError("limit"), "RESOURCE_LIMIT_EXCEEDED", 422),
        (UnsupportedMediaError("public address denied"), "URL_FORBIDDEN", 403),
        (UnsupportedMediaError("drm protected"), "VIDEO_DRM_PROTECTED", 422),
        (UnsupportedMediaError("provider unsupported"), "VIDEO_UNSUPPORTED", 422),
        (MediaExtractionError("extract"), "VIDEO_PARSE_FAILED", 422),
        (ValueError("bad"), "VIDEO_PARSE_FAILED", 422),
        (RuntimeError("bad"), "VIDEO_PARSE_FAILED", 422),
    ):
        failing = SimpleNamespace(inspect=AsyncMock(side_effect=exc))
        with pytest.raises(AppError) as raised:
            await inspect_media(
                payload, None, Response(), None, settings(), identity, failing
            )
        assert raised.value.code == code and raised.value.status_code == status
    with pytest.raises(AppError) as raised:
        await inspect_media(
            payload,
            None,
            Response(),
            None,
            settings(),
            identity,
            SimpleNamespace(inspect=lambda **_: None),
        )
    assert raised.value.code == "VIDEO_PARSE_FAILED"


@pytest.mark.asyncio
async def test_download_endpoints_and_error_translation() -> None:
    identity = SessionIdentity("token", "hash")
    job = download_result()
    payload = CreateDownloadRequest(
        source_id=uuid.uuid4(), format_id=uuid.uuid4(), client_request_id=uuid.uuid4()
    )
    publisher = SimpleNamespace(publish=AsyncMock())
    response = Response()
    result = await create_download(
        payload,
        None,
        response,
        None,
        settings(),
        identity,
        SimpleNamespace(create_download=AsyncMock(return_value=(job, True))),
        publisher,
    )
    assert result.id == job.id and response.status_code == 202
    publisher.publish.assert_awaited_once()
    replay = await create_download(
        payload,
        None,
        Response(),
        None,
        settings(),
        identity,
        SimpleNamespace(
            create_download=AsyncMock(return_value={"job": job, "created": False})
        ),
        None,
    )
    assert replay.id == job.id
    got = await get_download(job.id, identity, SimpleNamespace(get_job=lambda **_: job))
    assert got.id == job.id
    url = DownloadUrl(
        url="https://minio.test/object",
        expires_at=datetime.now(UTC),
        file_name="video.mp4",
    )
    assert (
        await create_download_url(
            job.id, None, identity, SimpleNamespace(download_url=lambda **_: url)
        )
    ).url.startswith("https://")
    with pytest.raises(AppError) as exc_info:
        await create_download_url(
            job.id, None, identity, SimpleNamespace(get_download_url=lambda **_: None)
        )
    assert exc_info.value.code == "JOB_NOT_READY"
    assert _job_and_created((job, False)) == (job, False)
    assert _job_and_created({"job": job, "created": 0}) == (job, False)
    assert _job_and_created(job) == (job, True)
    assert (
        _translate_repository_error(RuntimeError("not found")).code
        == "RESOURCE_NOT_FOUND"
    )
    assert (
        _translate_repository_error(RuntimeError("already used")).code
        == "IDEMPOTENCY_CONFLICT"
    )
    assert _translate_repository_error(RuntimeError("other")).code == "DOWNLOAD_FAILED"
    with pytest.raises(AppError) as raised:
        await create_download(
            payload,
            None,
            Response(),
            None,
            settings(),
            identity,
            SimpleNamespace(
                create_download=AsyncMock(side_effect=RuntimeError("already used"))
            ),
            None,
        )
    assert raised.value.code == "IDEMPOTENCY_CONFLICT"
    with pytest.raises(AppError) as raised:
        await create_download(
            payload,
            None,
            Response(),
            None,
            settings(),
            identity,
            SimpleNamespace(create_download=AsyncMock(return_value=(job, True))),
            SimpleNamespace(publish=AsyncMock(side_effect=RuntimeError("down"))),
        )
    assert raised.value.code == "QUEUE_PUBLISH_FAILED"
