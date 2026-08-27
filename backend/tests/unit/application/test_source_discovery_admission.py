import pytest
from app.application.source_discoveries.url_admission import canonicalize_article_url


def test_article_path_and_query_forms_are_canonicalized() -> None:
    assert (
        canonicalize_article_url("https://mp.weixin.qq.com/s/article_123")
        == "https://mp.weixin.qq.com/s/article_123"
    )
    assert (
        canonicalize_article_url("https://mp.weixin.qq.com/s?sn=s&idx=1&mid=2&__biz=b")
        == "https://mp.weixin.qq.com/s?__biz=b&idx=1&mid=2&sn=s"
    )


@pytest.mark.parametrize(
    "url",
    [
        "http://mp.weixin.qq.com/s/article_123",
        "https://mp.weixin.qq.com:8443/s/article_123",
        "https://mp.weixin.qq.com/s/article_123?ticket=secret",
        "https://mp.weixin.qq.com/s?__biz=b&mid=2&idx=1",
        "https://mp.weixin.qq.com/s?__biz=b&mid=2&idx=1&sn=s&ticket=secret",
        "https://mp.weixin.qq.com/s/article_123#fragment",
    ],
)
def test_article_admission_rejects_unsafe_or_incomplete_forms(url: str) -> None:
    with pytest.raises(ValueError):
        canonicalize_article_url(url)
