from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

from app.api.deps import get_current_user
from app.api.errors import register_exception_handlers
from app.api.responses import ApiResponseRoute
from app.api.routes.admin_operation_logs import router as logs_router
from app.core.db import create_session_factory
from app.core.errors import AppError
from app.models.operation_log import OperationLogRow
from app.repositories.operation_logs import OperationLogStore
from app.schemas.operation_logs import OperationLogResponse
from app.services.auth.models import CurrentUser, UserRole
from fastapi import APIRouter, FastAPI, Request
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select, text
from tests.postgres import isolated_postgres_engine


def account(role=UserRole.ADMIN):
    return CurrentUser(
        id=uuid4(),
        username="audit-admin",
        email="admin@example.test",
        role=role,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


async def test_admin_logs_authorization_and_global_results(postgres_engine):
    store = OperationLogStore(create_session_factory(postgres_engine))
    actor = account()
    entry = await store.begin(
        operation="updateUserAccess",
        description="更新用户权限",
        method="PATCH",
        route="/api/admin/users/{user_id}",
        resource_id=uuid4(),
    )
    await store.finish(
        entry, actor=actor, status_code=200, failed=False, error_code=None
    )
    app = FastAPI()
    app.state.services = SimpleNamespace(operation_log_store=store)
    app.include_router(logs_router)
    register_exception_handlers(app)
    app.dependency_overrides[get_current_user] = lambda: account(UserRole.USER)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (await client.get("/admin/operation-logs")).status_code == 403
        # A different administrator sees records across all users.
        app.dependency_overrides[get_current_user] = lambda: account()
        response = await client.get(
            "/admin/operation-logs", params={"admin_only": True}
        )
        assert response.status_code == 200
        assert response.headers["cache-control"] == "no-store"
        data = response.json()["data"]
        assert data["page_size"] == 10 and data["total"] == 1
        assert data["items"][0]["actor_id"] == str(actor.id)
        assert (
            await client.get("/admin/operation-logs", params={"page_size": 51})
        ).status_code == 422


async def test_request_durability_failure_redaction_and_resource_id(postgres_engine):
    sessions = create_session_factory(postgres_engine)
    store = OperationLogStore(sessions)
    actor = account()
    resource = uuid4()
    app = FastAPI()
    app.state.services = SimpleNamespace(operation_log_store=store)
    router = APIRouter(route_class=ApiResponseRoute)

    @router.post("/admin/resources", operation_id="createResource")
    async def create(request: Request) -> dict[str, str]:
        request.state.operation_actor = actor
        async with sessions() as session:
            assert (await session.scalar(select(OperationLogRow.outcome))) == "started"
        return {"id": str(resource), "secret": "DO_NOT_RETAIN"}

    @router.delete("/admin/resources/{id}", operation_id="deleteResource")
    async def remove(request: Request, id: str) -> None:
        request.state.operation_actor = actor
        raise AppError(
            status=403, code="forbidden", title="Forbidden", detail="DO_NOT_RETAIN"
        )

    app.include_router(router, prefix="/api")
    register_exception_handlers(app)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (
            await client.post(
                "/api/admin/resources?token=DO_NOT_RETAIN",
                json={"password": "DO_NOT_RETAIN"},
            )
        ).status_code == 200
        assert (
            await client.delete(f"/api/admin/resources/{resource}")
        ).status_code == 403
    result = await store.list(
        page=1,
        page_size=10,
        q=None,
        outcome=None,
        created_from=None,
        created_to=None,
        admin_only=False,
    )
    assert result.total == 2
    assert all(row.route.startswith("/api/admin/") for row in result.items)
    assert {row.outcome for row in result.items} == {"succeeded", "failed"}
    assert all(
        row.resource_id == resource and row.actor_id == actor.id for row in result.items
    )
    assert "DO_NOT_RETAIN" not in str(
        [
            OperationLogResponse.model_validate(row, from_attributes=True).model_dump()
            for row in result.items
        ]
    )
    # Final results cannot be overwritten by a delayed duplicate completion.
    await store.finish(
        result.items[0].id, actor=None, status_code=200, failed=False, error_code=None
    )
    again = await store.list(
        page=1,
        page_size=10,
        q=None,
        outcome="failed",
        created_from=None,
        created_to=None,
        admin_only=False,
    )
    assert again.total == 1


async def test_unavailable_audit_store_prevents_mutation():
    store = SimpleNamespace(
        begin=AsyncMock(side_effect=RuntimeError("unavailable")), finish=AsyncMock()
    )
    app = FastAPI()
    app.state.services = SimpleNamespace(operation_log_store=store)
    router = APIRouter(route_class=ApiResponseRoute)
    mutation = AsyncMock()

    @router.post("/change")
    async def change() -> None:
        await mutation()

    app.include_router(router)
    async with AsyncClient(
        transport=ASGITransport(app=app, raise_app_exceptions=False),
        base_url="http://test",
    ) as client:
        assert (await client.post("/change")).status_code == 500
    mutation.assert_not_called()


async def test_schema_repeat_and_task_events_survive_delete():
    sql = (Path(__file__).resolve().parents[2] / "sql/schema.sql").read_text()
    async with isolated_postgres_engine() as engine:
        async with engine.connect() as connection:
            schema = await connection.scalar(text("SELECT current_schema()"))
            assert schema.startswith("test_") and schema.replace("_", "").isalnum()
            await connection.execute(text(f'SET search_path TO "{schema}", public'))
            await connection.commit()
            raw = await connection.get_raw_connection()
            driver = raw.driver_connection
            await driver.execute(sql)
            # Exercise the same trigger on a minimal temporary fixture table.
            await driver.execute(
                "CREATE TABLE audit_task_fixture "
                "(id UUID PRIMARY KEY, status TEXT, error_code TEXT, "
                "deleted_at TIMESTAMPTZ)"
            )
            await driver.execute(
                "CREATE TRIGGER audit_fixture AFTER INSERT OR UPDATE OR DELETE "
                "ON audit_task_fixture FOR EACH ROW EXECUTE FUNCTION "
                "record_system_task_operation('测试任务')"
            )
            object_id = uuid4()
            await driver.execute(
                "INSERT INTO audit_task_fixture (id, status) VALUES ($1, 'queued')",
                object_id,
            )
            await driver.execute(
                "UPDATE audit_task_fixture SET status='failed', "
                "error_code='inspection_failed'"
            )
            await driver.execute("UPDATE audit_task_fixture SET status='failed'")
            await driver.execute("UPDATE audit_task_fixture SET deleted_at=now()")
            await driver.execute("DELETE FROM audit_task_fixture")
            await driver.execute(sql)
            rows = await driver.fetch(
                "SELECT * FROM operation_logs ORDER BY created_at"
            )
            assert [row["task_state"] for row in rows] == [
                "queued",
                "failed",
                "deleted",
                "deleted",
            ]
            assert all(
                row["resource_id"] == object_id and row["source"] == "task"
                for row in rows
            )
            assert rows[1]["outcome"] == "failed"
            assert (
                await driver.fetchval(
                    "SELECT count(*) FROM information_schema.triggers "
                    "WHERE trigger_name='operation_log_state_trigger' "
                    "AND trigger_schema=$1",
                    schema,
                )
                == 15
            )


async def test_provider_key_and_finalization_failure(postgres_engine, monkeypatch):
    from app.api.operation_logging import identify_operation_actor

    sessions = create_session_factory(postgres_engine)
    store = OperationLogStore(sessions)
    app = FastAPI()
    app.state.services = SimpleNamespace(operation_log_store=store)
    router = APIRouter(route_class=ApiResponseRoute)
    actor = account()

    @router.patch("/admin/providers/{provider_key}")
    async def change(provider_key: str) -> dict[str, str]:
        identify_operation_actor(actor)
        return {"key": provider_key, "api_key": "DO_NOT_RETAIN"}

    app.include_router(router, prefix="/api")
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        assert (
            await client.patch("/api/admin/providers/openrouter")
        ).status_code == 200
        monkeypatch.setattr(
            store, "finish", AsyncMock(side_effect=RuntimeError("unavailable"))
        )
        # The request already completed: do not turn logging failure into a
        # business retry. Its durable started record remains visible.
        assert (
            await client.patch("/api/admin/providers/openrouter")
        ).status_code == 200
    page = await store.list(
        page=1,
        page_size=10,
        q=None,
        outcome=None,
        created_from=None,
        created_to=None,
        admin_only=True,
    )
    assert page.total == 2
    assert page.items[0].outcome == "started"
    assert page.items[1].resource_key == "openrouter"
    assert page.items[1].actor_id == actor.id
    assert "DO_NOT_RETAIN" not in str(
        [
            OperationLogResponse.model_validate(row, from_attributes=True).model_dump()
            for row in page.items
        ]
    )
