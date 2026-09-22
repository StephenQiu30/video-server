import asyncio
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from app.api.deps import get_current_user
from app.core.config import Settings
from app.core.security.url_cipher import URLCipher
from app.integrations.url_security import FernetUrlEnvelope, MediaUrlValidator
from app.main import create_app
from app.models import MediaInspectionRow, OutboxEventRow, ResourceAdmissionRow
from app.repositories.downloads.intent_repository import IntentRepository
from app.repositories.downloads.repository import SqlAlchemyDownloadRepository
from app.services.download_execution.models import ExecutionDisposition
from app.services.downloads.errors import MediaInspectionTemporarilyUnavailable
from app.services.downloads.fingerprints import HmacRequestFingerprinter
from app.services.downloads.inspect_media import InspectMedia
from app.services.downloads.intent_execution import IntentExecution
from app.services.downloads.intents import IntentService
from app.services.quotas import UserQuota
from cryptography.fernet import Fernet
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker
from tests.integration.api.test_download_routes import TEST_USER
from tests.unit.services.fakes import FakeRunner
from tests.unit.services.test_inspect_media import runner_result

NOW = datetime(2026, 9, 22, tzinfo=UTC)
URL = "https://www.youtube.com/watch?v=BaW_jenozKc"


def components(engine, runner=None):
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    repo = IntentRepository(sessions)
    cipher = FernetUrlEnvelope(URLCipher(Fernet.generate_key()), key_id="test")
    fingerprint = HmacRequestFingerprinter(b"f" * 32)
    clock = [NOW]
    service = IntentService(
        repo,
        MediaUrlValidator(),
        cipher,
        fingerprint,
        now=lambda: clock[0],
        new_id=uuid4,
    )
    inspector = InspectMedia(
        repository=SqlAlchemyDownloadRepository(sessions),
        runner=runner or FakeRunner(runner_result()),
        url_validator=MediaUrlValidator(),
        url_cipher=cipher,
        fingerprinter=fingerprint,
        now=lambda: clock[0],
        new_id=uuid4,
        inspection_ttl=timedelta(minutes=15),
        max_duration_seconds=3600,
    )
    executor = IntentExecution(
        repo,
        inspector,
        cipher,
        worker_id="test-worker",
        clock=lambda: clock[0],
        heartbeat_interval=0.01,
    )
    return service, repo, executor, clock, sessions


async def test_api_accepts_before_parse_and_recovers_same_result(postgres_engine):
    service, repo, executor, _, sessions = components(postgres_engine)
    app = create_app(Settings(app_env="test"))
    app.state.services.intent_service = service
    app.dependency_overrides[get_current_user] = lambda: TEST_USER
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        created = await client.post(
            "/api/download-intents",
            json={"input": f"分享视频 {URL}"},
            headers={"Idempotency-Key": "same"},
        )
        assert created.status_code == 202
        assert created.headers["cache-control"] == "no-store"
        document = created.json()["data"]
        assert document["status"] == "queued" and document["inspection_id"] is None
        assert (
            not {"url", "owner_hash", "url_ciphertext", "lease_owner", "fence"}
            & document.keys()
        )
        async with sessions() as session:
            assert (
                await session.scalar(
                    select(func.count()).select_from(MediaInspectionRow)
                )
                == 0
            )
            assert (
                await session.scalar(select(func.count()).select_from(OutboxEventRow))
                == 1
            )
        intent_id = UUID(document["id"])
        assert await executor.execute(intent_id) is ExecutionDisposition.ACK
        observed = (await client.get(created.headers["location"])).json()["data"]
        assert observed["status"] == "ready" and observed["inspection_id"]
        repeated = await client.post(
            "/api/download-intents",
            json={"input": URL},
            headers={"Idempotency-Key": "same"},
        )
        assert repeated.status_code == 202 and repeated.json()["data"]["id"] == str(
            intent_id
        )
        assert await executor.execute(intent_id) is ExecutionDisposition.ACK
        async with sessions() as session:
            assert (
                await session.scalar(
                    select(func.count()).select_from(MediaInspectionRow)
                )
                == 1
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(ResourceAdmissionRow)
                )
                == 1
            )
        conflict = await client.post(
            "/api/download-intents",
            json={"input": URL + "1"},
            headers={"Idempotency-Key": "same"},
        )
        assert conflict.status_code == 409
        app.dependency_overrides[get_current_user] = lambda: replace(
            TEST_USER, id=uuid4()
        )
        assert (await client.get(created.headers["location"])).status_code == 404
        assert (
            await client.post(created.headers["location"] + "/cancel")
        ).status_code == 404
        app.dependency_overrides[get_current_user] = lambda: TEST_USER
        assert (await client.post(created.headers["location"] + "/cancel")).json()[
            "data"
        ]["status"] == "cancelled"
    assert (await repo.get(intent_id, TEST_USER.owner_hash)).status == "cancelled"


async def test_intent_quota_replay_and_cancellation(postgres_engine):
    service, _, _, _, sessions = components(postgres_engine)
    quota = UserQuota(max_active_per_owner=1)
    first = await service.create(URL, TEST_USER.owner_hash, "one", quota=quota)
    assert (
        await service.create(URL, TEST_USER.owner_hash, "one", quota=quota)
    ).id == first.id
    from app.services.quotas import QuotaExceeded

    with pytest.raises(QuotaExceeded, match="active_task_quota_exceeded"):
        await service.create(URL, TEST_USER.owner_hash, "two", quota=quota)
    await service.cancel(first.id, TEST_USER.owner_hash)
    await service.create(URL, TEST_USER.owner_hash, "two", quota=quota)
    async with sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(ResourceAdmissionRow))
            == 2
        )


class WaitingRunner(FakeRunner):
    def __init__(self):
        super().__init__(runner_result())
        self.entered = asyncio.Event()
        self.stopped = asyncio.Event()

    async def inspect(self, url, *, access_policy):
        self.entered.set()
        try:
            await asyncio.Event().wait()
        finally:
            self.stopped.set()


async def test_user_cancel_stops_execution_and_cannot_publish_result(postgres_engine):
    runner = WaitingRunner()
    service, repo, executor, _, sessions = components(postgres_engine, runner)
    intent = await service.create(URL, TEST_USER.owner_hash, "cancel")
    work = asyncio.create_task(executor.execute(intent.id))
    await asyncio.wait_for(runner.entered.wait(), 2)
    await service.cancel(intent.id, TEST_USER.owner_hash)
    assert await asyncio.wait_for(work, 2) is ExecutionDisposition.ACK
    assert runner.stopped.is_set()
    assert (await repo.get(intent.id, TEST_USER.owner_hash)).status == "cancelled"
    async with sessions() as session:
        assert (
            await session.scalar(select(func.count()).select_from(MediaInspectionRow))
            == 0
        )


async def test_worker_interruption_recovers_original_intent(postgres_engine):
    runner = WaitingRunner()
    service, repo, executor, clock, _ = components(postgres_engine, runner)
    intent = await service.create(URL, TEST_USER.owner_hash, "restart")
    work = asyncio.create_task(executor.execute(intent.id))
    await asyncio.wait_for(runner.entered.wait(), 2)
    work.cancel()
    with pytest.raises(asyncio.CancelledError):
        await work
    assert runner.stopped.is_set()
    clock[0] += timedelta(seconds=16)
    assert await repo.recover(now=clock[0]) == 1
    assert (await service.get(intent.id, TEST_USER.owner_hash)).status == "queued"


async def test_transient_failure_is_task_state_not_http_failure(postgres_engine):
    class Unavailable(FakeRunner):
        async def inspect(self, url, *, access_policy):
            raise MediaInspectionTemporarilyUnavailable

    service, repo, executor, clock, _ = components(
        postgres_engine, Unavailable(runner_result())
    )
    intent = await service.create(URL, TEST_USER.owner_hash, "retry")
    for attempt in range(3):
        assert await executor.execute(intent.id) is ExecutionDisposition.ACK
        observed = await service.get(intent.id, TEST_USER.owner_hash)
        assert observed.reason_code == "provider_temporarily_unavailable"
        if attempt < 2:
            assert observed.status == "retry_wait"
            clock[0] = observed.retry_at
            assert await repo.recover(now=clock[0]) == 1
        else:
            assert observed.status == "failed"


def test_openapi_intent_response_does_not_expose_execution_or_secrets():
    schema = create_app(Settings(app_env="test")).openapi()
    assert "202" in schema["paths"]["/api/download-intents"]["post"]["responses"]
    properties = schema["components"]["schemas"]["IntentResponse"]["properties"]
    assert (
        not {"url", "url_ciphertext", "owner_hash", "lease_owner", "fence"}
        & properties.keys()
    )
