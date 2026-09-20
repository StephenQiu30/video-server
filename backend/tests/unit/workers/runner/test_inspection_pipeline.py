from types import SimpleNamespace

import pytest
from app.services.provider_types import ProviderAccessMode
from app.workers.runner.errors import RunnerFailure
from app.workers.runner.inspection_pipeline import RunnerInspectionPipeline
from app.workers.runner.provider_registry import provider_request
from app.workers.runner.workspace import WorkspaceManager
from helpers import settings, split_media_info


async def test_provider_probe_failure_is_not_downgraded_to_incomplete_metadata(
    tmp_path,
) -> None:
    class Commands:
        async def inspect(self, *_args, **_kwargs):
            payload = split_media_info()
            payload["duration"] = None
            formats = payload["formats"]
            assert isinstance(formats, list)
            formats[0]["url"] = "https://media.example.com/video"
            return payload

        async def probe_remote(self, *_args, **_kwargs):
            raise RunnerFailure("provider_rate_limited", status=429)

    workspace = WorkspaceManager(tmp_path / "runner").create("probe-failure")
    try:
        with pytest.raises(RunnerFailure) as caught:
            await RunnerInspectionPipeline(settings(tmp_path), Commands()).inspect(
                provider_request("https://media.example.com/video"),
                workspace,
                context=SimpleNamespace(
                    provider_key="generic", access_mode=ProviderAccessMode.ANONYMOUS
                ),
                cookie_jar=None,
            )
        assert caught.value.code == "provider_rate_limited"
        assert caught.value.status == 429
    finally:
        workspace.cleanup()
