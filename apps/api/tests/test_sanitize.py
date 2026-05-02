from app.utils.sanitize import redact_url, safe_filename


def test_redact_url_sensitive_query() -> None:
    url = redact_url("https://example.com/video?id=1&token=secret&signature=abc")
    assert "token=%2A%2A%2A" in url
    assert "signature=%2A%2A%2A" in url
    assert "secret" not in url


def test_safe_filename_removes_path_separators() -> None:
    assert safe_filename("../a/b:c.mp4") == "_a_b_c.mp4"
