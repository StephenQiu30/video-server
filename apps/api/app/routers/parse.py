from typing import Annotated
from functools import lru_cache

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.deps import get_current_user
from app.models import User
from app.schemas import ParseRequest, ParseResponse
from app.services.download_adapter import DownloadEngineAdapter
from app.services.rate_limit import InMemoryRateLimiter
from app.utils.url import normalize_user_url

router = APIRouter(prefix="/api/parse", tags=["parse"])


@lru_cache
def get_parse_rate_limiter() -> InMemoryRateLimiter:
    settings = get_settings()
    return InMemoryRateLimiter(
        limit=settings.parse_rate_limit_per_minute,
        window_seconds=settings.parse_rate_limit_window_seconds,
    )


@router.post("", response_model=ParseResponse)
def parse_video(current_user: Annotated[User, Depends(get_current_user)], payload: ParseRequest) -> ParseResponse:
    get_parse_rate_limiter().assert_allowed(f"user:{current_user.id}")
    return DownloadEngineAdapter().parse(normalize_user_url(payload.url))
