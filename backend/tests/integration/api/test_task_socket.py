from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from app.api.routes.task_socket import _same_origin
from app.core.config import Settings
from app.infrastructure.realtime import RealtimeHub
from app.main import create_app
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

TASK_ID = UUID("55555555-5555-4555-8555-555555555555")


class FakeAuth:
    async def current_user(self, token: str):
        return SimpleNamespace(owner_hash="a" * 64) if token == "valid" else None


class FakeStore:
    async def replay(self, owner, task_type, task_id, after_version):
        if owner != "a" * 64 or task_id != TASK_ID:
            return None
        return (
            {
                "type": "task.updated",
                "event_id": "66666666-6666-4666-8666-666666666666",
                "task_type": task_type,
                "task_id": str(task_id),
                "version": after_version + 1,
                "status": "running",
            },
        )


class RacingStore(FakeStore):
    def __init__(self, hub: RealtimeHub) -> None:
        self.hub = hub

    async def replay(self, owner, task_type, task_id, after_version):
        replay = await super().replay(owner, task_type, task_id, after_version)
        await self.hub.publish(
            {
                "type": "task.updated",
                "event_id": "77777777-7777-4777-8777-777777777777",
                "task_type": task_type,
                "task_id": str(task_id),
                "version": after_version + 2,
                "status": "succeeded",
            }
        )
        return replay


def test_socket_auth_replay_and_subscription(tmp_path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    app.state.auth_service = FakeAuth()
    app.state.realtime_hub = RealtimeHub()
    app.state.task_event_store = FakeStore()
    client = TestClient(app)
    client.cookies.set("video_access_token", "valid")

    with client.websocket_connect("/api/ws/tasks") as socket:
        assert socket.receive_json()["protocol_version"] == 1
        socket.send_json(
            {
                "type": "subscribe",
                "tasks": [
                    {
                        "task_type": "analysis",
                        "task_id": str(TASK_ID),
                        "after_version": 3,
                    }
                ],
            }
        )
        assert socket.receive_json()["version"] == 4
        assert socket.receive_json()["type"] == "subscribed"


def test_socket_accepts_forwarded_frontend_origin(tmp_path) -> None:
    websocket = SimpleNamespace(
        headers={
            "origin": "https://frontend.example",
            "host": "api.internal:8111",
            "x-forwarded-host": "frontend.example",
        }
    )

    assert _same_origin(websocket, production=True)


def test_socket_rejects_missing_cookie(tmp_path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    app.state.auth_service = FakeAuth()
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as caught:
            with client.websocket_connect("/api/ws/tasks"):
                pass
    assert caught.value.code == 4401


def test_socket_buffers_events_during_replay_takeover(tmp_path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    app.state.auth_service = FakeAuth()
    hub = RealtimeHub()
    app.state.realtime_hub = hub
    app.state.task_event_store = RacingStore(hub)
    client = TestClient(app)
    client.cookies.set("video_access_token", "valid")

    with client.websocket_connect("/api/ws/tasks") as socket:
        socket.receive_json()
        socket.send_json(
            {
                "type": "subscribe",
                "tasks": [
                    {
                        "task_type": "analysis",
                        "task_id": str(TASK_ID),
                        "after_version": 3,
                    }
                ],
            }
        )
        assert socket.receive_json()["version"] == 4
        assert socket.receive_json()["type"] == "subscribed"
        assert socket.receive_json()["version"] == 5


def test_socket_enforces_owner_connection_limit(tmp_path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    app.state.auth_service = FakeAuth()
    app.state.realtime_hub = RealtimeHub(max_connections=2, max_per_owner=1)
    app.state.task_event_store = FakeStore()
    client = TestClient(app)
    client.cookies.set("video_access_token", "valid")

    with client.websocket_connect("/api/ws/tasks") as first:
        first.receive_json()
        with pytest.raises(WebSocketDisconnect) as caught:
            with client.websocket_connect("/api/ws/tasks"):
                pass
        assert caught.value.code == 4429


def test_socket_closes_when_owner_session_is_invalidated(tmp_path) -> None:
    app = create_app(Settings(app_env="test", frontend_dist_dir=tmp_path / "none"))
    app.state.auth_service = FakeAuth()
    hub = RealtimeHub()
    app.state.realtime_hub = hub
    app.state.task_event_store = FakeStore()
    client = TestClient(app)
    client.cookies.set("video_access_token", "valid")

    with client.websocket_connect("/api/ws/tasks") as socket:
        socket.receive_json()
        hub.invalidate_owner("a" * 64)
        with pytest.raises(WebSocketDisconnect) as caught:
            socket.receive_json()
        assert caught.value.code == 4401
