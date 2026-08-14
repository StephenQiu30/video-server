from datetime import timedelta

import pytest
from app.application.analysis import AnalysisPublish, PersistenceConflict
from tests.unit.domain.analysis.screenplay_factories import screenplay_analysis_result
from tests.unit.infrastructure.analysis.test_publish import NOW, validating_job


@pytest.mark.asyncio
async def test_video_job_rejects_screenplay_result_contract(analysis_db) -> None:
    command, job = await validating_job(analysis_db)

    with pytest.raises(PersistenceConflict, match="result contract differs"):
        await analysis_db.repository.publish_result(
            AnalysisPublish(
                job_id=command.id,
                run_id=command.run_id,
                result=screenplay_analysis_result(),
                lease_owner="worker-a",
                expected_version=job.version,
                provider="codex",
                model="controlled-model",
                cli_version="codex-cli controlled",
                now=NOW + timedelta(seconds=3),
            )
        )
