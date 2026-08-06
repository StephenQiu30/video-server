from __future__ import annotations

import time
from pathlib import Path

from app.runner.contracts import (
    CancelResponse,
    DownloadRequest,
    DownloadResponse,
    InspectResponse,
    MediaSummary,
    RunnerTaskStage,
    TaskStatusResponse,
)
from app.runner.settings import RunnerSettings
from app.runner.signing import HmacRequestAuthenticator, InMemoryNonceGuard

SECRET = "runner-shared-secret-material-at-least-32-bytes"


class FakeService:
    def __init__(self) -> None:
        self.inspected_url: str | None = None
        self.download_request: DownloadRequest | None = None
        self.cancelled: list[str] = []
        self.status_requests: list[str] = []

    async def inspect(self, url: str) -> InspectResponse:
        self.inspected_url = url
        return InspectResponse(
            media=MediaSummary(
                provider_media_id="fixture-id",
                title="Fixture",
                duration_seconds=60,
                extractor_key="Controlled",
            ),
            streams=[],
            options=[],
        )

    async def download(self, request: DownloadRequest) -> DownloadResponse:
        self.download_request = request
        return DownloadResponse.model_validate(
            {
                "task_id": request.task_id,
                "workspace_path": "/shared/job",
                "artifact": {
                    "relative_path": "artifact.mp4",
                    "size_bytes": 5,
                    "sha256": "a" * 64,
                    "duration_seconds": 60,
                    "container": "mp4",
                    "video_streams": 1,
                    "audio_streams": 1,
                },
            }
        )

    async def cancel(self, task_id: str) -> CancelResponse:
        self.cancelled.append(task_id)
        return CancelResponse(task_id=task_id)

    async def status(self, task_id: str) -> TaskStatusResponse:
        self.status_requests.append(task_id)
        return TaskStatusResponse(
            task_id=task_id,
            stage=RunnerTaskStage.DOWNLOADING,
            progress=40,
        )


def settings(tmp_path: Path) -> RunnerSettings:
    return RunnerSettings(
        runner_hmac_secret=SECRET,
        runner_egress_proxy="http://egress-proxy:3128",
        runner_workspace_root=tmp_path,
    )


def signed_headers(
    path: str,
    body: bytes,
    nonce: str,
    *,
    method: str = "POST",
) -> dict[str, str]:
    timestamp = int(time.time())
    signer = HmacRequestAuthenticator(
        SECRET.encode(),
        nonce_guard=InMemoryNonceGuard(ttl_seconds=60, max_entries=10),
        max_age_seconds=30,
        max_future_skew_seconds=5,
    )
    signature = signer.sign(method, path, body, timestamp, nonce)
    return {
        "X-Runner-Timestamp": str(timestamp),
        "X-Runner-Nonce": nonce,
        "X-Runner-Signature": signature,
        "Content-Type": "application/json",
    }
