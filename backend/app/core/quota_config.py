"""Typed deployment overrides for consumer admission budgets."""

from pydantic import BaseModel, ConfigDict, Field

from app.application.quotas import QuotaPolicy


class QuotaLimits(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    max_active_per_owner: int = Field(default=5, ge=1)
    max_active_global: int = Field(default=200, ge=1)
    daily_tasks: int = Field(default=50, ge=1)
    daily_bytes: int = Field(default=100 * 1024**3, ge=1)
    storage_bytes: int = Field(default=100 * 1024**3, ge=1)
    daily_analysis_attempts: int = Field(default=60, ge=1)

    def policy(self, **execution_limits: int) -> QuotaPolicy:
        return QuotaPolicy(**self.model_dump(), **execution_limits)
