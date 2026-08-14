from __future__ import annotations

from uuid import UUID

from app.application.analysis.get_analysis import GetAnalysis
from app.application.analysis.models import AnalysisJobView
from app.application.analysis.ports import AnalysisRepository
from app.application.analysis.validation import validate_owner_hash


class GetLatestDownloadAnalysis:
    def __init__(
        self, repository: AnalysisRepository, get_analysis: GetAnalysis
    ) -> None:
        self._repository = repository
        self._get_analysis = get_analysis

    async def __call__(
        self, download_id: UUID, owner_hash: str
    ) -> AnalysisJobView | None:
        owner_hash = validate_owner_hash(owner_hash)
        snapshot = await self._repository.get_latest_job_for_download(
            download_id, owner_hash
        )
        if snapshot is None:
            return None
        return await self._get_analysis(snapshot.id, owner_hash)


class GetLatestDocumentAnalysis:
    def __init__(
        self, repository: AnalysisRepository, get_analysis: GetAnalysis
    ) -> None:
        self._repository = repository
        self._get_analysis = get_analysis

    async def __call__(
        self, document_id: UUID, owner_hash: str
    ) -> AnalysisJobView | None:
        owner_hash = validate_owner_hash(owner_hash)
        snapshot = await self._repository.get_latest_job_for_document(
            document_id, owner_hash
        )
        if snapshot is None:
            return None
        return await self._get_analysis(snapshot.id, owner_hash)
