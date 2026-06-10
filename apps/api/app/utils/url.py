from ipaddress import ip_address
import re
from urllib.parse import urlparse

from app.core.errors import AppError

_LOCALHOST_PATTERNS = ("localhost", ".localhost", ".local", ".invalid")


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

    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise AppError("invalid_url", "请输入有效的视频链接，例如 https://example.com/video", 422)

    # Check restricted hosts before format validation so dangerous addresses get unsafe_url
    if _is_restricted_host(parsed.hostname):
        raise AppError("unsafe_url", "不允许访问本机地址、内网地址或保留地址", 422)

    if not _is_valid_host(parsed.hostname):
        raise AppError("invalid_url", "请输入有效的视频链接，例如 https://example.com/video", 422)

    return url


def _is_valid_host(hostname: str | None) -> bool:
    if not hostname:
        return False
    if "." in hostname:
        return True
    try:
        ip_address(hostname)
    except ValueError:
        return False
    return True


def _is_restricted_host(hostname: str | None) -> bool:
    """Reject localhost, private, loopback, link-local, multicast, reserved, and unspecified addresses."""
    if not hostname:
        return False
    lowered = hostname.lower()
    if any(lowered == pat or lowered.endswith(pat) for pat in _LOCALHOST_PATTERNS):
        return True
    try:
        address = ip_address(hostname)
    except ValueError:
        return False
    return any(
        [
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_multicast,
            address.is_reserved,
            address.is_unspecified,
        ]
    )
