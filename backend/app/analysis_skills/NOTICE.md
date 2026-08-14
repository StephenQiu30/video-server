# Analysis Skill third-party notices

The built-in screenplay skills are original, project-specific rewrites. They do not vendor or execute upstream scripts, prompts, examples, assets, MCP definitions, plugins, network calls, or sub-agent workflows.

## Agent Skills specification

- Source: https://github.com/agentskills/agentskills
- Reviewed commit: `69ef37e9424c0a7ea9dd2293b559e43ec8176379`
- License: repository code Apache-2.0; documentation CC-BY-4.0.
- Local use: adopted the `SKILL.md` YAML frontmatter shape and one-level reference convention. Product bindings remain namespaced and are validated by this repository.

## DirectorSKILL

- Source: https://github.com/wuwangzhang1216/DirectorSKILL
- Reviewed commit: `47db7d9b951a9f27f7b4b727a6ca0e01ab56f7c6`
- License: MIT; copyright 2026 wangzhang-wu.
- Local use: the screenplay analysis rules independently express evidence-based scene function, subtext, blocking/action observability, and actionable production thinking. Director-style overlays, concrete film expression, tool adapters, assets, and the upstream production pipeline were excluded.

## jwynia/agent-skills

- Source: https://github.com/jwynia/agent-skills
- Reviewed commit: `e02ec7e226a6e4f8419fd3b88a1d8e472d421b32`
- Reviewed skills: `story-analysis`, `scene-sequencing`, `dialogue`, and `character-arc`; each declares MIT in its frontmatter and identifies `jwynia` as author.
- Local use: the project independently implements conflict, scene function, causal progression, dialogue subtext/voice, and character choice/change as screenplay diagnostics. Deno scripts, session persistence, interactive workflows, examples, and cross-Skill orchestration were excluded.

## translate-book

- Source: https://github.com/deusyu/translate-book
- Reviewed commit: `5d07e733fa9318ff9c718085191c0c2243f51383`
- License: MIT; copyright 2025 Rainman.
- Local use: the rewrite rules independently adopt source fingerprints, glossary consistency, adjacent context, ordered chunks, coverage validation, and deterministic merge principles. Conversion tools, Calibre/Pandoc integration, scripts, arbitrary file writes, network access, and parallel sub-agents were excluded.

Updating any reviewed commit requires a fresh license and prompt-injection review, static fixtures, and real-provider E2E before release.
