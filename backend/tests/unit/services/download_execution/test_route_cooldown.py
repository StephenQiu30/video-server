from datetime import timedelta

from app.services.download_execution.models import ExecutionDisposition
from app.services.provider_route_admission import RouteCoolingDown
from tests.unit.services.download_execution.helpers import NOW, fixture
from tests.unit.services.download_execution.test_execution import artifact


async def test_new_cooldown_after_claim_preserves_attempt_and_delays_retry(tmp_path):
    case = fixture(artifact(tmp_path))
    deadline = NOW + timedelta(minutes=10)
    case.runner.error = RouteCoolingDown(deadline)
    assert await case.execution.execute(case.job_id) is ExecutionDisposition.ACK
    assert case.repository.failure["retry_at"] == deadline
    assert case.repository.failure["error_code"] == "provider_rate_limited"
    assert case.storage.uploads == []
