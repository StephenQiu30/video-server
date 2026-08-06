from __future__ import annotations

import json
from pathlib import Path

from api_helpers import FakeService, settings, signed_headers
from app.runner.main import create_app
from fastapi.testclient import TestClient


def test_health_is_public_and_inspect_requires_valid_raw_body_signature(
    tmp_path: Path,
) -> None:
    service = FakeService()
    client = TestClient(create_app(settings(tmp_path), service=service))
    body = json.dumps({"url": "https://media.example.com/video"}).encode()
    path = "/internal/v1/inspect"
    headers = signed_headers(path, body, "inspect_nonce_123456")

    assert client.get("/health/live").json() == {
        "service": "media-runner",
        "status": "live",
    }
    response = client.post(path, content=body, headers=headers)
    assert response.status_code == 200
    assert response.json()["media"]["title"] == "Fixture"
    assert response.json()["media"]["provider_media_id"] == "fixture-id"
    assert response.json()["media"]["extractor_key"] == "Controlled"
    assert service.inspected_url == "https://media.example.com/video"

    replay = client.post(path, content=body, headers=headers)
    assert replay.status_code == 401
    assert replay.json()["error"]["code"] == "request_replayed"


def test_tampered_or_unsigned_request_has_stable_error(tmp_path: Path) -> None:
    client = TestClient(create_app(settings(tmp_path), service=FakeService()))
    path = "/internal/v1/inspect"
    original = b'{"url":"https://media.example.com/video"}'
    headers = signed_headers(path, original, "tampered_nonce_12345")

    tampered = client.post(
        path,
        content=b'{"url":"https://evil.example/x"}',
        headers=headers,
    )
    unsigned = client.post(path, content=original)

    assert tampered.status_code == 401
    assert tampered.json()["error"]["code"] == "invalid_signature"
    assert unsigned.status_code == 401
    assert unsigned.json()["error"]["code"] == "authentication_required"

    query = client.post(f"{path}?unsigned=1", content=original, headers=headers)
    assert query.status_code == 422
    assert query.json()["error"]["code"] == "invalid_request"


def test_download_uses_signed_stable_contract(tmp_path: Path) -> None:
    service = FakeService()
    client = TestClient(create_app(settings(tmp_path), service=service))
    path = "/internal/v1/download"
    payload = {
        "task_id": "job_123",
        "url": "https://media.example.com/video",
        "expected_provider_media_id": "controlled",
        "expected_extractor_key": "Controlled",
        "plan": {
            "height": 1080,
            "width": 1920,
            "fps_bucket": "fps_30",
            "dynamic_range": "sdr",
            "video_codec_family": "h264",
            "audio_codec_family": "aac",
            "audio_language": "zh-CN",
            "container_preference": "mp4",
            "compatibility_profile": "balanced",
            "hints": {"video_id": "v", "audio_id": "a"},
        },
    }
    body = json.dumps(payload).encode()

    response = client.post(
        path,
        content=body,
        headers=signed_headers(path, body, "download_nonce_12345"),
    )

    assert response.status_code == 200
    assert response.json()["artifact"]["sha256"] == "a" * 64
    assert service.download_request is not None
    assert service.download_request.plan.height == 1080


def test_download_rejects_invalid_semantic_plan_before_service(tmp_path: Path) -> None:
    service = FakeService()
    client = TestClient(create_app(settings(tmp_path), service=service))
    path = "/internal/v1/download"
    body = json.dumps(
        {
            "task_id": "job_123",
            "url": "https://media.example.com/video",
            "expected_provider_media_id": "controlled",
            "expected_extractor_key": "Controlled",
            "plan": {
                "height": -1,
                "width": 1920,
                "fps_bucket": "fps_30",
                "dynamic_range": "sdr",
                "video_codec_family": "h264",
                "audio_codec_family": "aac",
                "container_preference": "mp4",
                "compatibility_profile": "balanced",
            },
        }
    ).encode()

    response = client.post(
        path,
        content=body,
        headers=signed_headers(path, body, "invalid_plan_nonce_12"),
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"
    assert service.download_request is None
