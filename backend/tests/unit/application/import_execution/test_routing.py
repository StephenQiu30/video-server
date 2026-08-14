from uuid import UUID

from app.application.import_execution import RoutedImportExecution
from app.application.imports import ImportDisposition
from app.domain.imports import ContentKind

RESOURCE_ID = UUID("cccccccc-cccc-4ccc-8ccc-cccccccccccc")


class Handler:
    def __init__(self) -> None:
        self.calls: list[ContentKind] = []

    async def execute(self, resource_id, content_kind, attempt, expected_version):
        self.calls.append(content_kind)
        return ImportDisposition.ACK


async def test_import_routing_is_selected_only_by_trusted_content_kind() -> None:
    video = Handler()
    document = Handler()
    router = RoutedImportExecution(video, document)

    await router.execute(RESOURCE_ID, ContentKind.VIDEO, 1, 1)
    await router.execute(RESOURCE_ID, ContentKind.SCREENPLAY, 1, 1)

    assert video.calls == [ContentKind.VIDEO]
    assert document.calls == [ContentKind.SCREENPLAY]
