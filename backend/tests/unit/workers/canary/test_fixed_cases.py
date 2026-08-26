from collections import defaultdict

from app.domain.providers import ProviderCanaryStage
from app.runner.provider_registry import current_provider_registry
from app.workers.canary.fixed_cases import fixed_public_diagnostic_targets

_KNOWN_INVALID_UPSTREAM_FIXTURES = {
    "BaW_jenozKc",
    "7206382937372134662",
}


def test_fixed_public_matrix_covers_every_registered_provider_and_stage() -> None:
    targets = fixed_public_diagnostic_targets()
    grouped: defaultdict[str, list] = defaultdict(list)
    for target in targets:
        grouped[target.provider_key].append(target)

    assert set(grouped) == {
        profile.key for profile in current_provider_registry().profiles
    }
    for provider_targets in grouped.values():
        assert {target.stage for target in provider_targets} == {
            ProviderCanaryStage.METADATA,
            ProviderCanaryStage.MEDIA,
        }
        assert len({target.target_id for target in provider_targets}) == 1
        assert len({target.safe_url() for target in provider_targets}) == 1


def test_fixed_public_matrix_does_not_reuse_known_invalid_upstream_fixtures() -> None:
    urls = tuple(
        target.safe_url() for target in fixed_public_diagnostic_targets()
    )

    assert all(
        marker not in url
        for marker in _KNOWN_INVALID_UPSTREAM_FIXTURES
        for url in urls
    )
