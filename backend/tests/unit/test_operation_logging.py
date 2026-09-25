from types import SimpleNamespace
from uuid import uuid4

from app.api.operation_logging import OperationLogRoute
from fastapi import APIRouter, FastAPI
from httpx import ASGITransport, AsyncClient


class _Store:
    def __init__(self) -> None:
        self.routes: list[str] = []

    async def begin(self, *, route: str, **_: object) -> object:
        self.routes.append(route)
        return uuid4()

    async def finish(self, *_: object, **__: object) -> None:
        return None


def _app(store: _Store) -> tuple[FastAPI, APIRouter]:
    router = APIRouter(route_class=OperationLogRoute, prefix="/items")

    @router.post("/{item_id}")
    async def touch(item_id: str) -> dict[str, str]:
        return {"id": item_id}

    app = FastAPI()
    app.state.services = SimpleNamespace(operation_log_store=store)
    return app, router


async def test_audited_route_records_public_template_on_every_request() -> None:
    store = _Store()
    app, router = _app(store)
    api = APIRouter(prefix="/api")
    api.include_router(router)
    app.include_router(api)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        for _ in range(2):
            assert (await client.post("/api/items/a")).status_code == 200
    assert store.routes == ["/api/items/{item_id}"] * 2


async def test_requests_rejected_before_execution_write_no_audit_row() -> None:
    from typing import Annotated

    from app.api.errors import register_exception_handlers
    from app.core.errors import AppError
    from fastapi import Depends
    from pydantic import BaseModel

    class Body(BaseModel):
        name: str

    def require_user() -> None:
        raise AppError(
            status=401, code="unauthenticated", title="Unauthorized", detail="x"
        )

    store = _Store()
    executed: list[str] = []
    router = APIRouter(route_class=OperationLogRoute)

    @router.post("/private")
    async def private(_: Annotated[None, Depends(require_user)]) -> None:
        executed.append("private")

    @router.post("/validated")
    async def validated(body: Body) -> None:
        executed.append(body.name)

    @router.post("/sync")
    def sync() -> dict[str, str]:
        executed.append("sync")
        return {"ok": "yes"}

    app = FastAPI()
    app.state.services = SimpleNamespace(operation_log_store=store)
    app.include_router(router)
    register_exception_handlers(app)
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # Anonymous or malformed traffic never reaches business code, so it
        # must not be able to grow the audit table.
        assert (await client.post("/private")).status_code == 401
        assert (await client.post("/validated", json={})).status_code == 422
        assert store.routes == []
        assert (await client.post("/validated", json={"name": "a"})).status_code == 200
        assert (await client.post("/sync")).status_code == 200
    assert store.routes == ["/validated", "/sync"]
    assert executed == ["a", "sync"]
