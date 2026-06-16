from __future__ import annotations

from app.core.errors import AppError, ErrorCode
from app.services.platforms import find_platform_profile
from app.sources.adapters.ytdlp import YtDlpAdapter, _classify_error
from app.sources.models import SourceRequest


class BilibiliAdapter(YtDlpAdapter):
    """Bilibili-specific adapter with platform-aware error messages."""

    @property
    def name(self) -> str:
        return "bilibili"

    def supports(self, request: SourceRequest) -> bool:
        profile = find_platform_profile(request.url)
        return bool(profile and profile.id == "bilibili")

    def map_error(self, exc: Exception) -> AppError:
        err = _classify_error(str(exc))
        if err.code == ErrorCode.PLATFORM_RESTRICTED:
            return AppError(
                ErrorCode.PLATFORM_RESTRICTED,
                "B 站内容存在访问限制，当前服务不会绕过登录、大会员、付费、版权或地区限制",
                403,
            )
        return err
