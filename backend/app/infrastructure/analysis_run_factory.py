"""Create initial and manually requested analysis execution runs."""

from datetime import datetime
from uuid import UUID

from app.infrastructure.database.models import AnalysisRunRow


def new_analysis_run(
    *,
    run_id: UUID,
    job_id: UUID,
    run_no: int,
    trigger: str,
    max_attempts: int,
    now: datetime,
) -> AnalysisRunRow:
    return AnalysisRunRow(
        id=run_id,
        job_id=job_id,
        run_no=run_no,
        trigger=trigger,
        max_attempts=max_attempts,
        created_at=now,
        updated_at=now,
    )
