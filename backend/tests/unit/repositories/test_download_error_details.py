from datetime import UTC, datetime
from uuid import uuid4

from app.models import DownloadJobRow
from app.repositories.download_repository import SqlAlchemyDownloadRepository
from app.schemas.downloads import DownloadResponse
from app.services.downloads.views import download_view
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker


async def test_persisted_failure_message_reaches_download_response(
    postgres_engine: AsyncEngine,
) -> None:
    sessions = async_sessionmaker(postgres_engine, expire_on_commit=False)
    job_id = uuid4()
    now = datetime.now(UTC)
    async with sessions.begin() as session:
        session.add(
            DownloadJobRow(
                id=job_id,
                source_kind="browser_import",
                inspection_id=None,
                format_id=None,
                owner_hash="a" * 64,
                idempotency_key="failure-message",
                request_fingerprint="b" * 64,
                semantic_plan={},
                status="failed",
                error_code="provider_content_restricted",
                error_message="内容访问受限",
                finished_at=now,
            )
        )
    repository = SqlAlchemyDownloadRepository(sessions)
    store = repository
    response = DownloadResponse.from_view(download_view(await store.get_job(job_id)))
    assert response.error_message == "内容访问受限"
