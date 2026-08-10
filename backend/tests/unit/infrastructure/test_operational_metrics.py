from datetime import UTC, datetime

import pytest
from app.infrastructure.database import Base, create_session_factory
from app.infrastructure.database.operational_counter import increment_counter
from app.infrastructure.operational_metrics import OperationalMetrics
from sqlalchemy.ext.asyncio import create_async_engine


@pytest.mark.asyncio
async def test_operational_metrics_use_fixed_low_cardinality_labels() -> None:
    engine = create_async_engine("sqlite+aiosqlite://")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    sessions = create_session_factory(engine)
    async with sessions() as session, session.begin():
        await increment_counter(session, "claim_noop", "analysis")
        await increment_counter(session, "claim_noop", "analysis")

    rendered = await OperationalMetrics(sessions).render(
        datetime(2026, 8, 10, tzinfo=UTC)
    )

    assert 'video_claim_noop_total{result="analysis"} 2' in rendered
    assert 'video_claim_noop_total{result="report"} 0' in rendered
    assert 'video_outbox_confirm_total{result="ack"} 0' in rendered
    assert 'video_outbox_unpublished{event_type="analysis.requested"} 0' in rendered
    assert (
        'video_outbox_oldest_seconds{event_type="analysis.requested"} 0.000' in rendered
    )
    assert 'video_analysis_jobs{state="queued"} 0' in rendered
    assert 'video_analysis_reports{state="publish_failed"} 0' in rendered
    assert "video_analysis_expired_leases 0" in rendered
    assert "video_analysis_technical_retries_total 0" in rendered
    assert all(
        sensitive not in rendered
        for sensitive in ("owner_hash", "job_id", "prompt", "object_key")
    )
    await engine.dispose()
