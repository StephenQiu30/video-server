from __future__ import annotations

TOOLS = (
    {
        "name": "probe_video",
        "description": "Read deterministic technical metadata for the complete video.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "inspect_video_overview",
        "description": (
            "Observe 16 evenly spaced frames from any bounded interval of the complete "
            "video as a 4x4 contact sheet. Start with the full duration, then refine."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "start_ms": {"type": "integer", "minimum": 0},
                "end_ms": {"type": "integer", "minimum": 1},
            },
            "required": ["start_ms", "end_ms"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True},
    },
    {
        "name": "inspect_video_frame",
        "description": (
            "Observe one exact video frame near a suspected boundary or highlight."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "timestamp_ms": {"type": "integer", "minimum": 0},
            },
            "required": ["timestamp_ms"],
            "additionalProperties": False,
        },
        "annotations": {"readOnlyHint": True},
    },
)
