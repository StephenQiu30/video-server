from __future__ import annotations


def valid_mapping() -> dict[str, object]:
    return {
        "schema_version": "visual-analysis.v1",
        "language": "zh-CN",
        "title": "Visual analysis",
        "summary": {"text": "grounded", "evidence_shot_ids": ["shot-a"]},
        "shots": [
            {
                "id": "shot-a",
                "index": 1,
                "start_ms": 0,
                "end_ms": 2_000,
                "representative_frame_ms": 1_000,
                "description": "Opening scene.",
                "transition_in": "none",
                "shot_size": "wide",
                "camera_motion": "static",
                "visual_tags": ["opening"],
            }
        ],
        "highlights": [],
        "assets": [],
    }
