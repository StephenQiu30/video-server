from __future__ import annotations

import argparse
import json
import sys

from .media_mcp import VideoObserver
from .media_mcp_tools import TOOLS


def _respond(identifier: object, result: object) -> None:
    print(
        json.dumps({"jsonrpc": "2.0", "id": identifier, "result": result}),
        flush=True,
    )


def _serve(observer: VideoObserver) -> None:
    for line in sys.stdin:
        message = json.loads(line)
        identifier = message.get("id")
        if identifier is None:
            continue
        method = message.get("method")
        if method == "initialize":
            version = message.get("params", {}).get("protocolVersion", "2025-06-18")
            _respond(
                identifier,
                {
                    "protocolVersion": version,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "video-observer", "version": "1.0"},
                },
            )
        elif method == "tools/list":
            _respond(identifier, {"tools": list(TOOLS)})
        elif method == "tools/call":
            params = message.get("params", {})
            _respond(
                identifier,
                observer.call(params.get("name", ""), params.get("arguments", {})),
            )
        else:
            _respond(identifier, {})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--workspace", required=True)
    parser.add_argument("--ffmpeg", required=True)
    parser.add_argument("--ffprobe", required=True)
    parser.add_argument("--duration-ms", required=True, type=int)
    parser.add_argument("--maximum-images", required=True, type=int)
    parser.add_argument("--maximum-image-bytes", required=True, type=int)
    _serve(VideoObserver(parser.parse_args()))


if __name__ == "__main__":
    main()
