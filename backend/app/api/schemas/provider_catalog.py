from __future__ import annotations

from datetime import datetime

from pydantic import Field, field_validator, model_validator

from app.api.schemas.common import StrictModel
from app.application.provider_catalog import ManagedProviderCatalogEntry
from app.domain.providers import ProviderSupportStatus


class ProviderCatalogEntryResponse(StrictModel):
    key: str
    display_name: str
    sort_order: int
    is_visible: bool
    system_registered: bool
    system_status: ProviderSupportStatus
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_view(
        cls, value: ManagedProviderCatalogEntry
    ) -> ProviderCatalogEntryResponse:
        entry = value.entry
        return cls(
            key=entry.key,
            display_name=entry.display_name,
            sort_order=entry.sort_order,
            is_visible=entry.is_visible,
            system_registered=value.system_registered,
            system_status=value.system_status,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )


class ProviderCatalogListResponse(StrictModel):
    items: tuple[ProviderCatalogEntryResponse, ...]


class CreateProviderCatalogEntryRequest(StrictModel):
    key: str = Field(min_length=1, max_length=32, pattern=r"^[a-z][a-z0-9_-]*$")
    display_name: str = Field(min_length=1, max_length=64)
    sort_order: int = Field(ge=0, le=10_000)
    is_visible: bool = True

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str) -> str:
        return _display_name(value)


class UpdateProviderCatalogEntryRequest(StrictModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=64)
    sort_order: int | None = Field(default=None, ge=0, le=10_000)
    is_visible: bool | None = None

    @field_validator("display_name")
    @classmethod
    def normalize_display_name(cls, value: str | None) -> str | None:
        return None if value is None else _display_name(value)

    @model_validator(mode="after")
    def require_change(self) -> UpdateProviderCatalogEntryRequest:
        if (
            self.display_name is None
            and self.sort_order is None
            and self.is_visible is None
        ):
            raise ValueError("at least one change is required")
        return self


def _display_name(value: str) -> str:
    normalized = " ".join(value.split())
    if not normalized:
        raise ValueError("display name is required")
    return normalized
