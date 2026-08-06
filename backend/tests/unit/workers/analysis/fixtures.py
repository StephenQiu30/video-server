from __future__ import annotations


def valid_mapping() -> dict[str, object]:
    statement = {"text": "grounded", "evidence_segment_ids": ["seg-a"]}
    return {
        "schema_version": "analysis.v1",
        "language": "zh-CN",
        "title": "Analysis",
        "summary": statement,
        "key_points": [statement],
        "action_items": [],
        "chapters": [
            {
                "title": "Chapter",
                "start_ms": 0,
                "end_ms": 2_000,
                "summary": "grounded",
                "evidence_segment_ids": ["seg-a"],
            }
        ],
        "mind_map": {
            "id": "root",
            "title": "Root",
            "summary": None,
            "start_ms": 0,
            "evidence_segment_ids": ["seg-a"],
            "children": [],
        },
    }
