---
name: framefetch
description: Use the FrameFetch Codex plugin to start, stop, or diagnose the local FrameFetch Agent and its Codex or Claude Code connections.
---

# FrameFetch Local Agent

Use this skill when the user asks about the FrameFetch local Agent, its lifecycle,
or whether Codex and Claude Code are ready on the current computer.

1. Call `framefetch_agent_status` for the normal readiness check. The MCP server
   starts the Agent automatically if it is not already running.
2. Call `framefetch_agent_doctor` when the user asks to refresh CLI detection or
   after they log in to Codex or Claude Code.
3. Call `framefetch_agent_start` or `framefetch_agent_stop` only for an explicit
   lifecycle request.
4. Explain `not_installed`, `login_required`, `timeout`, and `ready` as distinct
   states. Never claim a provider is usable unless `authenticated` is `true`.

The Agent only checks each provider through its official CLI. It does not read,
copy, return, or persist the provider's OAuth tokens. This plugin version exposes
the local control plane and diagnostics; submitting FrameFetch analysis jobs is a
separate capability and is not available through these tools yet.
