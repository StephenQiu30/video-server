"""Canonical aio-pika connection URL options shared by every process."""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def configured_rabbitmq_url(
    url: str,
    *,
    heartbeat: int,
    reconnect_interval: float,
    connection_name: str,
) -> str:
    if heartbeat < 10 or reconnect_interval <= 0 or not connection_name.strip():
        raise ValueError("invalid RabbitMQ connection settings")
    parsed = urlsplit(url)
    if parsed.scheme not in {"amqp", "amqps"} or parsed.hostname is None:
        raise ValueError("RabbitMQ URL must be an AMQP URL")
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    query.update(
        {
            "heartbeat": str(heartbeat),
            "reconnect_interval": f"{reconnect_interval:g}",
            # aiormq exposes the URL `name` parameter as connection_name.
            "name": connection_name.strip(),
        }
    )
    return urlunsplit(parsed._replace(query=urlencode(query)))
