from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


async def increment_counter(session: AsyncSession, metric: str, dimension: str) -> None:
    if (metric, dimension) not in {
        ("claim_noop", "analysis"),
        ("claim_noop", "report"),
        ("outbox_confirm", "ack"),
        ("outbox_confirm", "failed"),
    }:
        raise ValueError("unsupported operational counter")
    await session.execute(
        text(
            "INSERT INTO operational_counters (metric, dimension, value) "
            "VALUES (:metric, :dimension, 1) "
            "ON CONFLICT (metric, dimension) "
            "DO UPDATE SET value = operational_counters.value + 1"
        ),
        {"metric": metric, "dimension": dimension},
    )
