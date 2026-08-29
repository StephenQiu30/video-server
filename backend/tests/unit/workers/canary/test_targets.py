from app.domain.providers import ProviderAccessMode, ProviderCanaryStage
from app.workers.canary.targets import parse_canary_targets
from pydantic import SecretStr


def test_parses_authorized_https_targets_without_exposing_urls() -> None:
    targets = parse_canary_targets(
        SecretStr(
            '[{"target_id":"vimeo-owned-1","provider_key":"vimeo",'
            '"stage":"metadata","access_mode":"anonymous",'
            '"url":"https://vimeo.com/76979871"},'
            '{"target_id":"vimeo-owned-1","provider_key":"vimeo",'
            '"stage":"media","access_mode":"anonymous",'
            '"url":"https://vimeo.com/76979871"}]'
        )
    )

    assert len(targets) == 2
    assert targets[1].stage is ProviderCanaryStage.MEDIA
    assert targets[1].access_mode is ProviderAccessMode.ANONYMOUS
    assert "vimeo.com" not in repr(targets[0])


def test_rejects_insecure_mismatched_and_duplicate_targets() -> None:
    values = (
        '[{"target_id":"one","provider_key":"vimeo","stage":"metadata",'
        '"access_mode":"anonymous","url":"http://vimeo.com/76979871"}]',
        '[{"target_id":"one","provider_key":"youtube","stage":"metadata",'
        '"access_mode":"anonymous","url":"https://vimeo.com/76979871"}]',
        '[{"target_id":"one","provider_key":"vimeo","stage":"metadata",'
        '"access_mode":"anonymous",'
        '"url":"https://user:pass@vimeo.com/76979871"}]',
        '[{"target_id":"one","provider_key":"acfun","stage":"metadata",'
        '"access_mode":"anonymous","url":"https://www.acfun.cn/v/ac1"}]',
        '[{"target_id":"one","provider_key":"vimeo","stage":"metadata",'
        '"access_mode":"anonymous","url":"https://vimeo.com/76979871"},'
        '{"target_id":"one",'
        '"provider_key":"vimeo","stage":"metadata",'
        '"access_mode":"anonymous","url":"https://vimeo.com/22439234"}]',
        '[{"target_id":"one","provider_key":"vimeo","stage":"analysis",'
        '"access_mode":"anonymous","url":"https://vimeo.com/76979871"}]',
        '[{"target_id":"one","provider_key":"vimeo","stage":"metadata",'
        '"access_mode":"anonymous","url":"https://vimeo.com/76979871"},'
        '{"target_id":"one",'
        '"provider_key":"vimeo","stage":"media",'
        '"access_mode":"anonymous","url":"https://vimeo.com/22439234"}]',
        '[{"target_id":"one","provider_key":"vimeo","stage":"metadata",'
        '"url":"https://vimeo.com/76979871"}]',
        '[{"target_id":"one","provider_key":"tiktok","stage":"metadata",'
        '"access_mode":"operator_managed",'
        '"url":"https://www.tiktok.com/@creator/video/123"}]',
        '[{"target_id":"one","provider_key":"vimeo","stage":"metadata",'
        '"access_mode":"anonymous","url":"https://vimeo.com/76979871"},'
        '{"target_id":"one","provider_key":"vimeo","stage":"media",'
        '"access_mode":"operator_managed",'
        '"url":"https://vimeo.com/76979871"}]',
    )

    for value in values:
        try:
            parse_canary_targets(SecretStr(value))
        except ValueError as exc:
            assert str(exc) == "provider canary targets are invalid"
            assert "vimeo.com" not in str(exc)
        else:
            raise AssertionError("invalid target was accepted")
