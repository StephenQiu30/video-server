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
