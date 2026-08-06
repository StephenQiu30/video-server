"""Durable RabbitMQ topology for download requests and dead letters."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RabbitMqTopology:
    exchange: str
    download_queue: str
    download_routing_key: str
    message_ttl_ms: int = 1_800_000

    def __post_init__(self) -> None:
        for value in (self.exchange, self.download_queue, self.download_routing_key):
            if not value or value != value.strip():
                raise ValueError("RabbitMQ topology names cannot be blank")
        if self.message_ttl_ms <= 0:
            raise ValueError("message TTL must be positive")

    @property
    def dead_exchange(self) -> str:
        return f"{self.exchange}.dead"

    @property
    def dead_queue(self) -> str:
        return f"{self.download_queue}.dead"

    @property
    def dead_routing_key(self) -> str:
        return f"{self.download_queue}.dead"
