"""Administrator-managed Provider catalog without executable URL rules."""

from __future__ import annotations

import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Protocol

from app.application.auth import CurrentUser, UserRole
from app.application.providers import ProviderStatusView
from app.domain.providers import ProviderSupportStatus

_KEY = re.compile(r"[a-z][a-z0-9_-]{0,31}")


@dataclass(frozen=True, slots=True)
class ProviderCatalogEntry:
    key: str
    display_name: str
    sort_order: int
    is_visible: bool
    created_at: datetime
    updated_at: datetime


@dataclass(frozen=True, slots=True)
class ManagedProviderCatalogEntry:
    entry: ProviderCatalogEntry
    system_registered: bool
    system_status: ProviderSupportStatus


class ProviderCatalogErrorCode(StrEnum):
    FORBIDDEN = "forbidden"
    INVALID_ENTRY = "invalid_provider_catalog_entry"
    CONFLICT = "provider_catalog_conflict"
    NOT_FOUND = "provider_catalog_not_found"


class ProviderCatalogError(RuntimeError):
    def __init__(self, code: ProviderCatalogErrorCode) -> None:
        self.code = code
        super().__init__(code.value)


class DuplicateProviderCatalogKeyError(RuntimeError):
    pass


class ProviderCatalogRepository(Protocol):
    async def list_entries(
        self, *, visible_only: bool = False
    ) -> tuple[ProviderCatalogEntry, ...]: ...

    async def create_entry(
        self,
        *,
        key: str,
        display_name: str,
        sort_order: int,
        is_visible: bool,
        now: datetime,
    ) -> ProviderCatalogEntry: ...

    async def update_entry(
        self,
        key: str,
        *,
        display_name: str | None,
        sort_order: int | None,
        is_visible: bool | None,
        now: datetime,
    ) -> ProviderCatalogEntry | None: ...

    async def delete_entry(self, key: str, *, now: datetime) -> bool: ...


class ProviderCatalogService:
    def __init__(
        self,
        repository: ProviderCatalogRepository,
        baselines: tuple[ProviderStatusView, ...],
        *,
        now: Callable[[], datetime],
    ) -> None:
        self._repository = repository
        self._baselines = {item.key: item for item in baselines}
        self._now = now

    async def list_entries(
        self, actor: CurrentUser
    ) -> tuple[ManagedProviderCatalogEntry, ...]:
        _require_admin(actor)
        return tuple(
            self._managed(item) for item in await self._repository.list_entries()
        )

    async def create_entry(
        self,
        actor: CurrentUser,
        *,
        key: str,
        display_name: str,
        sort_order: int,
        is_visible: bool,
    ) -> ManagedProviderCatalogEntry:
        _require_admin(actor)
        key, display_name = _validated(key, display_name, sort_order)
        try:
            entry = await self._repository.create_entry(
                key=key,
                display_name=display_name,
                sort_order=sort_order,
                is_visible=is_visible,
                now=self._now(),
            )
        except DuplicateProviderCatalogKeyError as exc:
            raise ProviderCatalogError(ProviderCatalogErrorCode.CONFLICT) from exc
        return self._managed(entry)

    async def update_entry(
        self,
        actor: CurrentUser,
        key: str,
        *,
        display_name: str | None,
        sort_order: int | None,
        is_visible: bool | None,
    ) -> ManagedProviderCatalogEntry:
        _require_admin(actor)
        normalized_key = _validated_key(key)
        normalized_name = None
        if display_name is not None:
            normalized_name = _validated_name(display_name)
        if sort_order is not None and not 0 <= sort_order <= 10_000:
            raise ProviderCatalogError(ProviderCatalogErrorCode.INVALID_ENTRY)
        entry = await self._repository.update_entry(
            normalized_key,
            display_name=normalized_name,
            sort_order=sort_order,
            is_visible=is_visible,
            now=self._now(),
        )
        if entry is None:
            raise ProviderCatalogError(ProviderCatalogErrorCode.NOT_FOUND)
        return self._managed(entry)

    async def delete_entry(self, actor: CurrentUser, key: str) -> None:
        _require_admin(actor)
        if not await self._repository.delete_entry(
            _validated_key(key), now=self._now()
        ):
            raise ProviderCatalogError(ProviderCatalogErrorCode.NOT_FOUND)

    def _managed(self, entry: ProviderCatalogEntry) -> ManagedProviderCatalogEntry:
        baseline = self._baselines.get(entry.key)
        return ManagedProviderCatalogEntry(
            entry=entry,
            system_registered=bool(baseline and baseline.registered),
            system_status=(
                baseline.status
                if baseline is not None
                else ProviderSupportStatus.UNSUPPORTED
            ),
        )


def _require_admin(actor: CurrentUser) -> None:
    if actor.role is not UserRole.ADMIN:
        raise ProviderCatalogError(ProviderCatalogErrorCode.FORBIDDEN)


def _validated(key: str, display_name: str, sort_order: int) -> tuple[str, str]:
    if not 0 <= sort_order <= 10_000:
        raise ProviderCatalogError(ProviderCatalogErrorCode.INVALID_ENTRY)
    return _validated_key(key), _validated_name(display_name)


def _validated_key(key: str) -> str:
    normalized = key.strip().casefold()
    if _KEY.fullmatch(normalized) is None:
        raise ProviderCatalogError(ProviderCatalogErrorCode.INVALID_ENTRY)
    return normalized


def _validated_name(display_name: str) -> str:
    normalized = " ".join(display_name.split())
    if not 1 <= len(normalized) <= 64:
        raise ProviderCatalogError(ProviderCatalogErrorCode.INVALID_ENTRY)
    return normalized
