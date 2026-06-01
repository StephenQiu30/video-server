---
name: harness-local-server
description: Use when a project must become bootable for unattended agents, including local setup, one-command startup, readiness checks, logs, and documented environment requirements.
license: MIT
---

# Harness Local Server

## Purpose

Make the project bootable before orchestration. Symphony-style execution only closes the loop when a fresh workspace can start the system without hidden local knowledge.

## Use When

- A ticket requires app, API, worker, or integration behavior to run locally.
- Startup depends on undocumented shell history, manual services, or private env values.
- The agent cannot tell whether the system is ready for end-to-end validation.

## Standard Contract

The repository should expose:

- `env.example`: required variables, safe defaults, secret source, and local/CI differences.
- install command: dependency setup for a fresh workspace.
- start command: `make start`, `scripts/start-local.sh`, `npm run dev`, or equivalent.
- health check: command or endpoint that proves the system is bootable and ready.
- logs: exact paths or commands for app, worker, browser, and test logs.
- stop/cleanup command: frees ports and background processes.

## Flow

1. Inventory existing scripts, CI jobs, container files, README, and `docs/operations/`.
2. Prefer existing project conventions; add thin wrappers only when repeated steps are currently implicit.
3. Document env setup without committing secrets.
4. Start the system from a clean shell and run the health check.
5. Record command, port, health result, and logs location in `## Claude Workpad`.
6. If startup fails, preserve logs and make the next fix against the harness, not a one-off manual step.

## Done

- A fresh workspace can install, start, health check, validate, and stop the system from documented commands.
- Failure output tells the next agent where to inspect logs.
- `WORKFLOW.md` setup hooks can call the same documented commands.
