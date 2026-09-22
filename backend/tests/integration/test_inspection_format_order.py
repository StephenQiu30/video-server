from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from app.repositories.downloads.media_repository import MediaRepository
from app.services.downloads.inspection_models import FormatCreate, InspectionCreate
from app.services.downloads.plans import plan_fingerprint, plan_to_documents
from app.services.downloads.rules.enums import AudioCodecFamily
from app.services.downloads.views import inspection_view
from app.workers.runner.metadata import normalize_metadata
from app.workers.runner.options import build_download_options
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


def options():
    inspection = normalize_metadata(
        {
            "id": "owned-sample",
            "title": "Owned sample",
            "duration": 30,
            "extractor_key": "Controlled",
            "formats": [
                {
                    "format_id": "silent-4k",
                    "ext": "webm",
                    "width": 3840,
                    "height": 2160,
                    "fps": 30,
                    "vcodec": "av01",
                    "acodec": "none",
                },
                {
                    "format_id": "video-1080",
                    "ext": "mp4",
                    "width": 1920,
                    "height": 1080,
                    "fps": 30,
                    "vcodec": "h264",
                    "acodec": "none",
                },
                {
                    "format_id": "audio",
                    "ext": "m4a",
                    "vcodec": "none",
                    "acodec": "mp4a.40.2",
                    "abr": 128,
                },
                {
                    "format_id": "muxed-720",
                    "ext": "mp4",
                    "width": 1280,
                    "height": 720,
                    "fps": 30,
                    "vcodec": "h264",
                    "acodec": "aac",
                },
            ],
        },
        max_duration_seconds=60,
        max_candidate_streams=20,
    )
    return inspection.streams


def test_default_keeps_audio_before_resolution_and_before_option_limit():
    plans = build_download_options(options(), max_options=10)
    assert [(plan.height, plan.audio_codec_family) for plan in plans] == [
        (1080, AudioCodecFamily.AAC),
        (720, AudioCodecFamily.AAC),
        (2160, AudioCodecFamily.NONE),
    ]
    assert build_download_options(options(), max_options=1) == plans[:1]
    assert build_download_options(tuple(reversed(options())), max_options=10) == plans


async def test_persisted_inspection_and_idempotent_replay_keep_runner_recommendation(
    postgres_engine: AsyncEngine,
):
    repository = MediaRepository(
        async_sessionmaker(postgres_engine, expire_on_commit=False)
    )
    now = datetime(2026, 9, 23, tzinfo=UTC)
    plans = build_download_options(options(), max_options=10)
    formats = []
    for index, plan in enumerate(plans):
        semantic, hints = plan_to_documents(plan)
        formats.append(
            FormatCreate(
                id=UUID(int=len(plans) - index),
                display_name=f"{plan.height}p",
                plan_fingerprint=plan_fingerprint(semantic),
                semantic_plan=semantic,
                provider_hints=hints,
                expires_at=now + timedelta(hours=1),
            )
        )
    command = InspectionCreate(
        id=uuid4(),
        owner_hash="a" * 64,
        idempotency_key="format-order",
        request_fingerprint="b" * 64,
        url_ciphertext=b"encrypted",
        url_nonce=b"nonce",
        url_key_id="test",
        extractor_key="Controlled",
        provider_media_id="owned-sample",
        title="Owned sample",
        duration_seconds=30,
        metadata={},
        expires_at=now + timedelta(hours=1),
        formats=tuple(formats),
    )
    saved = await repository.save_inspection(command)
    loaded = await repository.get_inspection(command.id, command.owner_hash, now)
    replay = await repository.save_inspection(command)
    # Deliberately put silent video first in database UUID order.
    assert loaded.formats[0].id != saved.inspection.formats[0].id
    first = inspection_view(saved.inspection).formats
    assert inspection_view(loaded).formats == first
    assert inspection_view(replay.inspection).formats == first
    assert first[0].plan is not None
    assert first[0].plan.audio_codec_family is AudioCodecFamily.AAC
    assert first[0].plan.height == 1080
