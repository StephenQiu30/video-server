from dataclasses import replace

import pytest
from app.domain.provider_access import ProviderAccessPolicy as Policy
from app.domain.providers import ProviderAccessMode as Mode
from app.integrations.media_runner import MediaRunnerRouter
from app.services.downloads.errors import (
    MediaInspectionConfigurationMissing,
    MediaInspectionFailure,
    MediaInspectionPolicyNotAllowed,
)
from tests.unit.infrastructure.test_media_runner_router import FakeClient, context

URL = "https://www.youtube.com/watch?v=owned"


async def test_explicit_public_never_touches_configured_operator() -> None:
    anonymous = FakeClient(replace(context(Mode.ANONYMOUS), provider_key="youtube"))
    operator = FakeClient(context(Mode.OPERATOR_MANAGED))
    operator.inspect_error = AssertionError("must not access session")
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]
    result = await router.inspect(URL, access_policy=Policy.PUBLIC)
    assert result.access_context.access_mode is Mode.ANONYMOUS
    assert anonymous.inspected == [URL]
    assert operator.inspected == []


@pytest.mark.parametrize("requested", [None, Policy.OPERATOR_PUBLIC])
async def test_missing_controlled_route_is_not_anonymous_fallback(requested) -> None:
    anonymous = FakeClient(context(Mode.ANONYMOUS))
    router = MediaRunnerRouter(anonymous)  # type: ignore[arg-type]
    with pytest.raises(MediaInspectionConfigurationMissing):
        await router.inspect(URL, access_policy=requested)
    assert anonymous.inspected == []


@pytest.mark.parametrize("requested", [Policy.PUBLIC_SESSION, Policy.PERSONAL_ENTITLED])
async def test_unadmitted_policy_never_reaches_any_runner(requested) -> None:
    anonymous = FakeClient(context(Mode.ANONYMOUS))
    operator = FakeClient(context(Mode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]
    with pytest.raises(MediaInspectionPolicyNotAllowed):
        await router.inspect(URL, access_policy=requested)
    assert anonymous.inspected == operator.inspected == []


@pytest.mark.parametrize("mismatch", ["mode", "provider"])
async def test_misconfigured_runner_cannot_silently_change_policy(mismatch) -> None:
    wrong = (
        context(Mode.OPERATOR_MANAGED)
        if mismatch == "mode"
        else replace(context(Mode.ANONYMOUS), provider_key="instagram")
    )
    anonymous = FakeClient(wrong)
    router = MediaRunnerRouter(anonymous)  # type: ignore[arg-type]
    with pytest.raises(MediaInspectionFailure, match="context mismatch"):
        await router.inspect(URL, access_policy=Policy.PUBLIC)
    assert anonymous.inspected == [URL]


async def test_public_failure_is_not_retried_with_more_privilege() -> None:
    anonymous = FakeClient(context(Mode.ANONYMOUS))
    anonymous.inspect_error = MediaInspectionFailure()
    operator = FakeClient(context(Mode.OPERATOR_MANAGED))
    router = MediaRunnerRouter(anonymous, {"youtube": operator})  # type: ignore[arg-type]
    with pytest.raises(MediaInspectionFailure):
        await router.inspect(URL, access_policy=Policy.PUBLIC)
    assert anonymous.inspected == [URL]
    assert operator.inspected == []


async def test_explicit_deployment_default_does_not_change_when_an_operator_appears():
    anonymous = FakeClient(replace(context(Mode.ANONYMOUS), provider_key="youtube"))
    operator = FakeClient(context(Mode.OPERATOR_MANAGED))
    for operators in ({}, {"youtube": operator}):
        router = MediaRunnerRouter(
            anonymous, operators, default_policies={"youtube": Policy.PUBLIC}
        )  # type: ignore[arg-type]
        assert (await router.inspect(URL)).access_context.access_mode is Mode.ANONYMOUS
    assert anonymous.inspected == [URL, URL]
    assert operator.inspected == []


def test_unadmitted_deployment_default_is_rejected_before_startup():
    anonymous = FakeClient(context(Mode.ANONYMOUS))
    with pytest.raises(ValueError, match="not admitted"):
        MediaRunnerRouter(
            anonymous, default_policies={"youtube": Policy.PUBLIC_SESSION}
        )  # type: ignore[arg-type]
