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


def valid_screenplay_mapping() -> dict[str, object]:
    evidence = {
        "id": "act-1",
        "title": "建立",
        "description": "建立人物目标。",
        "evidence_scene_ids": ["scene-1"],
    }
    return {
        "language": "zh-CN",
        "title": "剧本分析",
        "logline": "一位剪辑师必须在首映前找回丢失的结局。",
        "synopsis": "主人公追查素材并重新理解自己的创作选择。",
        "structure": {
            "acts": [evidence],
            "turning_points": [],
            "pacing_summary": "开场紧凑，转折清晰。",
        },
        "characters": [
            {
                "id": "character-1",
                "name": "林舟",
                "goal": "找回结局",
                "conflict": "必须面对自己的删改",
                "arc": "从逃避转向承担",
                "evidence_scene_ids": ["scene-1"],
            }
        ],
        "scenes": [
            {
                "id": "analysis-scene-1",
                "source_scene_id": "scene-1",
                "purpose": "建立危机",
                "conflict": "时间不足",
                "turn": "发现备份线索",
                "pacing": "快速",
                "findings": ["目标明确"],
            }
        ],
        "dialogue_findings": [],
        "strengths": [evidence],
        "priority_revisions": [
            {
                "id": "revision-1",
                "title": "强化阻力",
                "description": "让危机更早影响人物选择。",
                "evidence_scene_ids": ["scene-1"],
            }
        ],
    }
