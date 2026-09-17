#!/usr/bin/env python3
"""MCP bridge that starts and controls the FrameFetch local agent."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from framefetch_agent import ensure_agent, probe_agent, read_endpoint, request_agent

MCP_VERSION = "0.1.0"
EMPTY_INPUT_SCHEMA = {
    "type": "object",
    "properties": {},
    "additionalProperties": False,
}

TOOLS = (
    {
        "name": "framefetch_agent_status",
        "description": (
            "Start the local FrameFetch Agent when needed and report whether Codex "
            "and Claude Code are installed and authenticated."
        ),
        "inputSchema": EMPTY_INPUT_SCHEMA,
    },
    {
        "name": "framefetch_agent_doctor",
        "description": "Refresh local Codex and Claude Code connection diagnostics.",
        "inputSchema": EMPTY_INPUT_SCHEMA,
    },
    {
        "name": "framefetch_agent_start",
        "description": "Start the local FrameFetch Agent and return its status.",
        "inputSchema": EMPTY_INPUT_SCHEMA,
    },
    {
        "name": "framefetch_agent_stop",
        "description": "Stop the local FrameFetch Agent started for the current user.",
        "inputSchema": EMPTY_INPUT_SCHEMA,
    },
)


def _tool_result(payload: dict[str, Any], *, is_error: bool = False) -> dict[str, Any]:
    result: dict[str, Any] = {
        "content": [
            {
                "type": "text",
                "text": json.dumps(payload, ensure_ascii=False, indent=2),
            }
        ],
        "structuredContent": payload,
    }
    if is_error:
        result["isError"] = True
    return result


def _call_tool(name: str) -> dict[str, Any]:
    try:
        if name in {
            "framefetch_agent_status",
            "framefetch_agent_start",
        }:
            script_path = Path(__file__).with_name("framefetch_agent.py")
            status = ensure_agent(script_path)
            provider_states = status.get("providers", {}).values()
            still_checking = any(
                provider.get("status") == "checking" for provider in provider_states
            )
            if still_checking:
                status = request_agent("POST", "/v1/diagnostics")
            return _tool_result(status)
        if name == "framefetch_agent_doctor":
            ensure_agent(Path(__file__).with_name("framefetch_agent.py"))
            return _tool_result(request_agent("POST", "/v1/diagnostics"))
        if name == "framefetch_agent_stop":
            endpoint = read_endpoint()
            if endpoint is None or probe_agent(endpoint) is None:
                return _tool_result({"stopped": True, "wasRunning": False})
            response = request_agent("POST", "/v1/stop", endpoint=endpoint)
            return _tool_result(
                {
                    "stopped": bool(response.get("stopping")),
                    "wasRunning": True,
                }
            )
        return _tool_result({"error": f"Unknown tool: {name}"}, is_error=True)
    except (ConnectionError, TimeoutError, OSError) as error:
        return _tool_result({"error": str(error)}, is_error=True)


def _respond(identifier: object, result: object) -> None:
    print(
        json.dumps({"jsonrpc": "2.0", "id": identifier, "result": result}),
        flush=True,
    )


def _error(identifier: object, code: int, message: str) -> None:
    print(
        json.dumps(
            {
                "jsonrpc": "2.0",
                "id": identifier,
                "error": {"code": code, "message": message},
            }
        ),
        flush=True,
    )


def serve() -> None:
    startup_error: str | None = None
    try:
        ensure_agent(Path(__file__).with_name("framefetch_agent.py"))
    except (ConnectionError, TimeoutError, OSError) as error:
        startup_error = str(error)
    for line in sys.stdin:
        try:
            message = json.loads(line)
        except json.JSONDecodeError:
            _error(None, -32700, "Parse error")
            continue
        identifier = message.get("id")
        if identifier is None:
            continue
        method = message.get("method")
        if method == "initialize":
            protocol_version = message.get("params", {}).get(
                "protocolVersion", "2025-06-18"
            )
            _respond(
                identifier,
                {
                    "protocolVersion": protocol_version,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": {"name": "framefetch", "version": MCP_VERSION},
                    **({"instructions": startup_error} if startup_error else {}),
                },
            )
        elif method == "tools/list":
            _respond(identifier, {"tools": list(TOOLS)})
        elif method == "tools/call":
            params = message.get("params", {})
            _respond(identifier, _call_tool(str(params.get("name", ""))))
        elif method == "ping":
            _respond(identifier, {})
        else:
            _error(identifier, -32601, "Method not found")


if __name__ == "__main__":
    serve()
