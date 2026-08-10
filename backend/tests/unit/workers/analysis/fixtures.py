from __future__ import annotations


def valid_mapping() -> dict[str, object]:
    return {
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
                "narrative_function": "建立开场空间与叙事基调。",
                "highlight_score": 3,
                "visual_tags": ["opening"],
            }
        ],
        "highlights": [],
        "assets": [],
        "production_advice": {
            "summary": "优先还原开场镜头的空间关系与视觉基调。",
            "priority_shot_ids": ["shot-a"],
            "recommended_extensions": ["镜头 Prompt", "场景资产"],
        },
    }
