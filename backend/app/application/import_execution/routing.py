from __future__ import annotations

from typing import Protocol
from uuid import UUID

from app.application.imports import ImportDisposition
from app.domain.imports import ContentKind


class ImportExecutionHandler(Protocol):
    async def execute(
        self,
        resource_id: UUID,
        content_kind: ContentKind,
        attempt: int,
        expected_version: int,
    ) -> ImportDisposition: ...


class RoutedImportExecution:
    def __init__(
        self, video: ImportExecutionHandler, document: ImportExecutionHandler
    ) -> None:
        self._video = video
        self._document = document

    async def execute(
        self,
        resource_id: UUID,
        content_kind: ContentKind,
        attempt: int,
        expected_version: int,
    ) -> ImportDisposition:
        handler = self._video if content_kind is ContentKind.VIDEO else self._document
        return await handler.execute(
            resource_id, content_kind, attempt, expected_version
        )
