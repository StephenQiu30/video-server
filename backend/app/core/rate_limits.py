"""Validated deployment defaults for operation admission."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

RateLimitOperation = Literal[
    "login",
    "register",
    "inspect",
    "download",
    "download_retry",
    "media_import",
    "media_import_upload",
    "document_import",
    "document_import_upload",
    "analysis",
    "analysis_retry",
]


class RateLimitPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    limit: int = Field(ge=1, le=100_000)
    window_seconds: int = Field(ge=1, le=86400)


def default_rate_limits() -> dict[RateLimitOperation, RateLimitPolicy]:
    return {
        "login": RateLimitPolicy(limit=10, window_seconds=60),
        "register": RateLimitPolicy(limit=5, window_seconds=3600),
        "inspect": RateLimitPolicy(limit=20, window_seconds=60),
        "download": RateLimitPolicy(limit=10, window_seconds=60),
        "download_retry": RateLimitPolicy(limit=5, window_seconds=60),
        "media_import": RateLimitPolicy(limit=10, window_seconds=60),
        "media_import_upload": RateLimitPolicy(limit=30, window_seconds=60),
        "document_import": RateLimitPolicy(limit=10, window_seconds=60),
        "document_import_upload": RateLimitPolicy(limit=30, window_seconds=60),
        "analysis": RateLimitPolicy(limit=5, window_seconds=60),
        "analysis_retry": RateLimitPolicy(limit=5, window_seconds=60),
    }
