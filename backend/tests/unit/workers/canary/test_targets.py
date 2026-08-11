from app.domain.providers import ProviderCanaryStage
from app.workers.canary.targets import parse_canary_targets
from pydantic import SecretStr


def test_parses_authorized_https_targets_without_exposing_urls() -> None:
    targets = parse_canary_targets(
        SecretStr(
            '[{"target_id":"acfun-owned-1","provider_key":"acfun",'
            '"stage":"metadata","url":"https://www.acfun.cn/v/ac1"},'
            '{"target_id":"acfun-owned-1","provider_key":"acfun",'
            '"stage":"media","url":"https://www.acfun.cn/v/ac1"}]'
        )
    )

    assert len(targets) == 2
    assert targets[1].stage is ProviderCanaryStage.MEDIA
    assert "acfun.cn" not in repr(targets[0])


def test_rejects_insecure_mismatched_and_duplicate_targets() -> None:
    values = (
        '[{"target_id":"one","provider_key":"acfun","stage":"metadata",'
        '"url":"http://www.acfun.cn/v/ac1"}]',
        '[{"target_id":"one","provider_key":"vimeo","stage":"metadata",'
        '"url":"https://www.acfun.cn/v/ac1"}]',
        '[{"target_id":"one","provider_key":"acfun","stage":"metadata",'
        '"url":"https://user:pass@www.acfun.cn/v/ac1"}]',
        '[{"target_id":"one","provider_key":"acfun","stage":"metadata",'
        '"url":"https://www.acfun.cn/bangumi/aa1"}]',
        '[{"target_id":"one","provider_key":"acfun","stage":"metadata",'
        '"url":"https://www.acfun.cn/v/ac1"},{"target_id":"one",'
        '"provider_key":"acfun","stage":"metadata",'
        '"url":"https://www.acfun.cn/v/ac2"}]',
    )

    for value in values:
        try:
            parse_canary_targets(SecretStr(value))
        except ValueError as exc:
            assert str(exc) == "provider canary targets are invalid"
            assert "acfun.cn" not in str(exc)
        else:
            raise AssertionError("invalid target was accepted")
