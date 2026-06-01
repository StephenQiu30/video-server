"""Tests for enhanced artifacts collection (subtitles, cover, metadata).

Acceptance: 字幕、封面、元数据可用时随任务归档并可在任务详情中展示。
增强产物失败或不可用只记录事件或增强状态，不把主视频任务回退为失败。
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import DownloadTask, User
from app.core.security import create_access_token
from video_downloader_shared.states import TaskState
from worker.enhanced_artifacts import collect_enhanced_artifacts
from worker.domain import EnhancedArtifactsStatus


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _make_user(session: Session, *, email: str, github_id: str) -> User:
    user = User(email=email, display_name=email.split("@")[0], github_id=github_id)
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


# ---------------------------------------------------------------------------
# Unit tests for collect_enhanced_artifacts
# ---------------------------------------------------------------------------


def test_collect_enhanced_artifacts_with_all_available(tmp_path) -> None:
    """当字幕、封面、元数据全部可用时，全部采集并返回 COLLECTED 状态。"""
    subtitle_file = tmp_path / "test_video.zh-CN.srt"
    subtitle_file.write_text("1\n00:00:01,000 --> 00:00:02,000\n你好世界\n")

    info_dict = {
        "subtitles": {
            "zh-CN": [
                {"ext": "srt", "url": "https://example.com/sub.srt", "_filename": str(subtitle_file)},
            ],
        },
        "thumbnail": "https://example.com/cover.jpg",
        "description": "这是一个测试视频的描述",
        "uploader": "测试上传者",
        "upload_date": "20260101",
        "duration": 120,
        "view_count": 10000,
        "like_count": 500,
        "tags": ["测试", "视频"],
        "categories": ["娱乐"],
    }

    result = collect_enhanced_artifacts(info_dict, tmp_path)

    assert result.status == EnhancedArtifactsStatus.COLLECTED
    assert result.subtitle_data is not None
    assert "zh-CN" in result.subtitle_data
    assert result.subtitle_data["zh-CN"]["ext"] == "srt"
    assert result.video_metadata is not None
    assert result.video_metadata["uploader"] == "测试上传者"
    assert result.video_metadata["duration"] == 120
    assert result.video_metadata["tags"] == ["测试", "视频"]


def test_collect_enhanced_artifacts_partial_failure(tmp_path) -> None:
    """当部分增强产物不可用时，采集可用的部分并返回 PARTIAL 状态。"""
    info_dict = {
        "subtitles": {},  # 无字幕
        "thumbnail": "https://example.com/cover.jpg",
        "description": "视频描述",
        "uploader": "上传者",
        "upload_date": "20260101",
        "duration": 60,
        "view_count": 5000,
        "like_count": 200,
    }

    result = collect_enhanced_artifacts(info_dict, tmp_path)

    assert result.status == EnhancedArtifactsStatus.PARTIAL
    assert result.subtitle_data is None
    assert result.video_metadata is not None
    assert result.video_metadata["uploader"] == "上传者"


def test_collect_enhanced_artifacts_unavailable(tmp_path) -> None:
    """当没有增强产物数据时，返回 UNAVAILABLE 状态且不抛异常。"""
    info_dict: dict = {}

    result = collect_enhanced_artifacts(info_dict, tmp_path)

    assert result.status == EnhancedArtifactsStatus.UNAVAILABLE
    assert result.subtitle_data is None
    assert result.video_metadata is None


def test_collect_enhanced_artifacts_does_not_raise_on_malformed_info(tmp_path) -> None:
    """畸形的 info_dict 不应导致异常。"""
    info_dict = {
        "subtitles": "not-a-dict",  # type: ignore[arg-type]
        "thumbnail": None,
        "description": None,
    }

    result = collect_enhanced_artifacts(info_dict, tmp_path)

    assert result.status == EnhancedArtifactsStatus.UNAVAILABLE


def test_collect_enhanced_artifacts_extracts_metadata_minimal(tmp_path) -> None:
    """只提供 uploader 也能采集部分元数据。"""
    info_dict = {
        "uploader": "最小上传者",
    }

    result = collect_enhanced_artifacts(info_dict, tmp_path)

    assert result.status == EnhancedArtifactsStatus.PARTIAL
    assert result.video_metadata is not None
    assert result.video_metadata["uploader"] == "最小上传者"


# ---------------------------------------------------------------------------
# Integration test: enhanced fields appear in task detail endpoint
# ---------------------------------------------------------------------------


def test_task_detail_includes_enhanced_fields_when_populated(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    """任务详情 API 返回增强产物字段。"""
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)

    owner = _make_user(session, email="enhanced@example.com", github_id="enhanced-owner")
    token = create_access_token(owner.id)
    headers = {"Authorization": f"Bearer {token}"}

    task = DownloadTask(
        user_id=owner.id,
        source_url="https://bilibili.com/video/BV1test",
        title="增强字段测试",
        state=TaskState.SUCCEEDED.value,
        object_key="users/1/tasks/test/video.mp4",
        output_filename="video.mp4",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
        enhanced_status=EnhancedArtifactsStatus.COLLECTED.value,
        subtitle_data='{"zh-CN": {"ext": "srt", "content": "1\\n00:00:01,000 --> 00:00:02,000\\n你好"}}',
        video_metadata='{"uploader": "测试UP主", "duration": 120}',
    )
    session.add(task)
    session.commit()

    response = client.get(f"/api/tasks/{task.id}", headers=headers)
    assert response.status_code == 200

    detail = response.json()
    assert detail["enhanced_status"] == EnhancedArtifactsStatus.COLLECTED.value
    assert detail["subtitle_data"] is not None
    assert "zh-CN" in detail["subtitle_data"]
    assert detail["video_metadata"] is not None
    assert detail["video_metadata"]["uploader"] == "测试UP主"


def test_task_detail_enhanced_fields_null_when_not_enhanced(
    monkeypatch,
    client: TestClient,
    session: Session,
) -> None:
    """未增强的任务详情中增强字段为 null。"""
    monkeypatch.setattr("app.routers.tasks.enqueue_download_task", lambda task_id: None)

    owner = _make_user(session, email="noenhanced@example.com", github_id="noenhanced-owner")
    token = create_access_token(owner.id)
    headers = {"Authorization": f"Bearer {token}"}

    task = DownloadTask(
        user_id=owner.id,
        source_url="https://bilibili.com/video/BV1test2",
        title="无增强字段测试",
        state=TaskState.SUCCEEDED.value,
        object_key="users/1/tasks/test2/video.mp4",
        output_filename="video.mp4",
        expires_at=datetime.now(UTC) + timedelta(hours=24),
    )
    session.add(task)
    session.commit()

    response = client.get(f"/api/tasks/{task.id}", headers=headers)
    assert response.status_code == 200

    detail = response.json()
    assert detail["enhanced_status"] is None
    assert detail["subtitle_data"] is None
    assert detail["video_metadata"] is None
