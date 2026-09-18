from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from app.domain.downloads import DownloadErrorCode
from app.domain.downloads.content_restrictions import ContentRestriction
from app.runner.errors import RunnerFailure
from app.services.download_execution.errors import classify_runner_failure
from app.services.downloads.errors import MediaInspectionPaidContentRestricted
from tests.unit.services.fakes import FakeRepository
from tests.unit.services.test_inspect_media import OWNER, runner_result, use_case


@pytest.mark.parametrize("reason", list(ContentRestriction))
async def test_recognized_restriction_is_inspectable_but_never_downloadable(
    reason, monkeypatch
) -> None:
    repository = FakeRepository()
    inspect, runner, _ = use_case(repository, runner_result())
    monkeypatch.setattr(
        runner,
        "inspect",
        AsyncMock(side_effect=MediaInspectionPaidContentRestricted(reason)),
    )
    view = await inspect("https://www.bilibili.com/video/BV1xx411c7mD", OWNER, "paid-1")
    assert view.access_decision.value == "blocked"
    assert view.restriction_reason == reason.value
    assert view.formats == ()
    assert view.duration_seconds == 0
    assert view.rights_basis is None
    assert view.protection_state.value == "unknown"
    assert view.identity_state.value == "unknown"
    assert view.user_action
    assert view.extractor_key == "bilibili"
    assert (
        classify_runner_failure(RunnerFailure(reason.value, status=422))
        is DownloadErrorCode.PROVIDER_CONTENT_RESTRICTED
    )
