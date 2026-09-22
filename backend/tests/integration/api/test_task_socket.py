from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from app.api.browser_origin import same_browser_origin
from app.core.config import Settings
from app.integrations.realtime import RealtimeHub
from app.main import create_app
from fastapi.testclient import TestClient
from starlette.requests import HTTPConnection
from starlette.websockets import WebSocketDisconnect

TASK_ID = UUID("55555555-5555-4555-8555-555555555555")


class FakeAuth:
    async def current_user(self, token: str, *, touch: bool):
        assert touch is False
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
    app = create_app(Settings(app_env="test"))
    app.state.services.web_session_service = FakeAuth()
    app.state.services.realtime_hub = RealtimeHub()
    app.state.services.task_event_store = FakeStore()
    client = TestClient(app)
    client.cookies.set("video_web_session", "valid")

    with client.websocket_connect(
        "/api/ws/tasks", headers={"origin": "http://testserver"}
    ) as socket:
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


@pytest.mark.parametrize(
    ("origin", "host", "forwarded", "peer", "expected"),
    [
        ("https://frontend.example", "api:8111", "frontend.example", "127.0.0.1", True),
        ("https://evil.example", "api:8111", "evil.example", "198.51.100.1", False),
        ("http://127.0.0.1:8101", "127.0.0.1:8111", None, "127.0.0.1", False),
        ("http://testserver", "testserver", None, "127.0.0.1", True),
        (None, "testserver", None, "127.0.0.1", False),
    ],
)
def test_socket_exact_origin(origin, host, forwarded, peer, expected):
    headers = {"host": host}
    if origin is not None:
        headers["origin"] = origin
    if forwarded:
        headers.update({"x-forwarded-host": forwarded, "x-forwarded-proto": "https"})
    socket = HTTPConnection(
        {
            "type": "websocket",
            "scheme": "ws",
            "path": "/api/ws/tasks",
            "client": (peer, 1000),
            "headers": [(k.encode(), v.encode()) for k, v in headers.items()],
        }
    )
    assert same_browser_origin(socket, Settings(app_env="test")) is expected


def test_socket_rejects_missing_cookie(tmp_path) -> None:
    app = create_app(Settings(app_env="test"))
    app.state.services.web_session_service = FakeAuth()
    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as caught:
            with client.websocket_connect(
                "/api/ws/tasks", headers={"origin": "http://testserver"}
            ):
                pass
    assert caught.value.code == 4401


def test_socket_buffers_events_during_replay_takeover(tmp_path) -> None:
    app = create_app(Settings(app_env="test"))
    app.state.services.web_session_service = FakeAuth()
    hub = RealtimeHub()
    app.state.services.realtime_hub = hub
    app.state.services.task_event_store = RacingStore(hub)
    client = TestClient(app)
    client.cookies.set("video_web_session", "valid")

    with client.websocket_connect(
        "/api/ws/tasks", headers={"origin": "http://testserver"}
    ) as socket:
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
    app = create_app(Settings(app_env="test"))
    app.state.services.web_session_service = FakeAuth()
    app.state.services.realtime_hub = RealtimeHub(max_connections=2, max_per_owner=1)
    app.state.services.task_event_store = FakeStore()
    client = TestClient(app)
    client.cookies.set("video_web_session", "valid")

    with client.websocket_connect(
        "/api/ws/tasks", headers={"origin": "http://testserver"}
    ) as first:
        first.receive_json()
        with pytest.raises(WebSocketDisconnect) as caught:
            with client.websocket_connect(
                "/api/ws/tasks", headers={"origin": "http://testserver"}
            ):
                pass
        assert caught.value.code == 4429


def test_socket_closes_when_owner_session_is_invalidated(tmp_path) -> None:
    app = create_app(Settings(app_env="test"))
    app.state.services.web_session_service = FakeAuth()
    hub = RealtimeHub()
    app.state.services.realtime_hub = hub
    app.state.services.task_event_store = FakeStore()
    client = TestClient(app)
    client.cookies.set("video_web_session", "valid")

    with client.websocket_connect(
        "/api/ws/tasks", headers={"origin": "http://testserver"}
    ) as socket:
        socket.receive_json()
        hub.invalidate_owner("a" * 64)
        with pytest.raises(WebSocketDisconnect) as caught:
            socket.receive_json()
        assert caught.value.code == 4401


@pytest.mark.parametrize("unavailable", [True, False])
def test_socket_monitor_distinguishes_dependency_outage_from_revocation(unavailable):
    from app.core.errors import AppError
    from app.services.auth.errors import AuthError, AuthErrorCode

    class ChangingAuth(FakeAuth):
        def __init__(self):
            self.first = True

        async def current_user(self, token, *, touch):
            assert touch is False
            if self.first:
                self.first = False
                return SimpleNamespace(owner_hash="a" * 64)
            if unavailable:
                raise AppError(
                    status=503,
                    code="service_unavailable",
                    title="Unavailable",
                    detail="Retry",
                )
            raise AuthError(AuthErrorCode.UNAUTHENTICATED)

    app = create_app(Settings(app_env="test", websocket_auth_recheck_seconds=1))
    app.state.services.web_session_service = ChangingAuth()
    app.state.services.realtime_hub = RealtimeHub()
    app.state.services.task_event_store = FakeStore()
    with TestClient(app) as client:
        client.cookies.set("video_web_session", "valid")
        with client.websocket_connect(
            "/api/ws/tasks", headers={"origin": "http://testserver"}
        ) as socket:
            assert socket.receive_json()["type"] == "hello"
            with pytest.raises(WebSocketDisconnect) as caught:
                socket.receive_json()
            assert caught.value.code == (1013 if unavailable else 4401)
