"""Authenticated same-origin task status WebSocket."""

from __future__ import annotations

import asyncio
from contextlib import suppress
from urllib.parse import urlsplit
from uuid import UUID

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.application.auth import AuthError
from app.infrastructure.realtime import (
    RealtimeConnection,
    RealtimeConnectionLimit,
    RealtimeHub,
)
from app.infrastructure.task_event_store import TaskEventStore

router = APIRouter(tags=["realtime"])


@router.websocket("/ws/tasks")
async def task_socket(websocket: WebSocket) -> None:
    settings = websocket.app.state.settings
    if not _same_origin(websocket, settings.app_env == "production"):
        await websocket.close(code=4403)
        return
    token = websocket.cookies.get(settings.auth_access_cookie_name)
    try:
        user = await websocket.app.state.auth_service.current_user(token or "")
    except (AuthError, AttributeError):
        user = None
    if user is None:
        await websocket.close(code=4401)
        return
    hub: RealtimeHub = websocket.app.state.realtime_hub
    store: TaskEventStore = websocket.app.state.task_event_store
    try:
        connection = hub.register(user.owner_hash)
    except RealtimeConnectionLimit:
        await websocket.close(code=4429)
        return
    await websocket.accept()
    await _send_json(
        websocket,
        connection,
        {
            "type": "hello",
            "connection_id": str(connection.id),
            "heartbeat_seconds": 25,
            "protocol_version": 1,
        },
    )
    writer = asyncio.create_task(_write_events(websocket, connection))
    session_monitor = asyncio.create_task(
        _monitor_session(
            websocket,
            connection,
            websocket.app.state.auth_service,
            token or "",
            user,
            settings.websocket_auth_recheck_seconds,
        )
    )
    try:
        while True:
            message = await websocket.receive_json()
            await _subscribe(websocket, connection, hub, store, message)
    except (WebSocketDisconnect, ValueError, TypeError):
        pass
    finally:
        hub.unregister(connection)
        writer.cancel()
        session_monitor.cancel()
        await asyncio.gather(writer, session_monitor, return_exceptions=True)


async def _subscribe(
    websocket: WebSocket,
    connection: RealtimeConnection,
    hub: RealtimeHub,
    store: TaskEventStore,
    message: object,
) -> None:
    if not isinstance(message, dict) or set(message) != {"type", "tasks"}:
        raise ValueError
    tasks = message["tasks"]
    if message["type"] not in {"subscribe", "resync"} or not isinstance(tasks, list):
        raise ValueError
    if not 1 <= len(tasks) <= 32:
        raise ValueError
    for item in tasks:
        if not isinstance(item, dict) or set(item) != {
            "task_type",
            "task_id",
            "after_version",
        }:
            raise ValueError
        task_type = item["task_type"]
        task_id = UUID(str(item["task_id"]))
        after = item["after_version"]
        if task_type not in {"download", "analysis"} or type(after) is not int:
            raise ValueError
        hub.begin_subscription(connection, task_type, task_id)
        replay = await store.replay(connection.owner_hash, task_type, task_id, after)
        if replay is None:
            hub.abort_subscription(connection, task_type, task_id)
            await _send_json(
                websocket,
                connection,
                {"type": "subscription.rejected", "task_id": str(task_id)},
            )
            continue
        for event in replay:
            await _send_json(websocket, connection, event)
        await _send_json(
            websocket,
            connection,
            {
                "type": "subscribed",
                "task_type": task_type,
                "task_id": str(task_id),
                "version": after if not replay else replay[-1]["version"],
            },
        )
        hub.finish_subscription(connection, task_type, task_id)


async def _write_events(websocket: WebSocket, connection: RealtimeConnection) -> None:
    while True:
        event = await connection.queue.get()
        if event.get("type") == "session.invalidated":
            await websocket.close(code=4401)
            return
        with suppress(WebSocketDisconnect):
            await _send_json(websocket, connection, event)


async def _monitor_session(
    websocket: WebSocket,
    connection: RealtimeConnection,
    auth_service: object,
    token: str,
    original_user: object,
    interval: float,
) -> None:
    original_identity = _identity(original_user)
    while True:
        await asyncio.sleep(interval)
        try:
            current = await auth_service.current_user(token)  # type: ignore[attr-defined]
        except (AuthError, AttributeError):
            current = None
        if current is None or _identity(current) != original_identity:
            await websocket.close(code=4401)
            return
        await _send_json(websocket, connection, {"type": "heartbeat"})


def _identity(user: object) -> tuple[object, object, object]:
    return (
        getattr(user, "id", None),
        getattr(user, "role", None),
        getattr(user, "owner_hash", None),
    )


async def _send_json(
    websocket: WebSocket,
    connection: RealtimeConnection,
    event: dict[str, object],
) -> None:
    async with connection.send_lock:
        await websocket.send_json(event)


def _same_origin(websocket: WebSocket, production: bool) -> bool:
    origin = websocket.headers.get("origin")
    host = websocket.headers.get("host")
    if origin is None or host is None:
        return not production
    parsed = urlsplit(origin)
    return parsed.netloc == host and (not production or parsed.scheme == "https")
