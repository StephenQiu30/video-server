from ipaddress import ip_address
import re
from urllib.parse import urlparse

from app.core.errors import AppError


def normalize_user_url(value: str) -> str:
    url = (value or "").strip()
    if not url:
        raise AppError("invalid_url", "请输入视频链接", 422)

    # Extract the clean URL first if the user pasted a raw share text block containing extra copy
    url_pattern = re.compile(r'https?://[a-zA-Z0-9.\-_~:/?#\[\]@!$&\'()*+,;=]+')
    match = url_pattern.search(url)
    if match:
        url = match.group(0).strip()

    if any(char.isspace() for char in url):
        raise AppError("invalid_url", "请输入有效的视频链接，例如 https://example.com/video", 422)

    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    if parsed.scheme not in {"http", "https"} or not parsed.netloc or not _is_valid_host(parsed.hostname):
        raise AppError("invalid_url", "请输入有效的视频链接，例如 https://example.com/video", 422)

    return url


def _is_valid_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if hostname == "localhost" or "." in hostname:
        return True
    try:
        ip_address(hostname)
    except ValueError:
        return False
    return True
