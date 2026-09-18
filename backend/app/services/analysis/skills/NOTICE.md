# Analysis Skill third-party notices

The built-in analysis skills are original, project-specific rewrites. They do not vendor or execute upstream scripts, prompts, examples, assets, MCP definitions, plugins, network calls, or sub-agent workflows.

## Agent Skills specification

- Source: https://github.com/agentskills/agentskills
- Reviewed commit: `69ef37e9424c0a7ea9dd2293b559e43ec8176379`
- License: repository code Apache-2.0; documentation CC-BY-4.0.
- Local use: adopted the `SKILL.md` YAML frontmatter shape and one-level reference convention. Product bindings remain namespaced and are validated by this repository.

## DirectorSKILL

- Source: https://github.com/wuwangzhang1216/DirectorSKILL
- Reviewed commit: `47db7d9b951a9f27f7b4b727a6ca0e01ab56f7c6`
- License: MIT; copyright 2026 wangzhang-wu.
- Local use: the screenplay and director-breakdown rules independently express evidence-based scene function, observable blocking, shot purpose, edit relationships, continuity anchors, and actionable production thinking. Upstream examples, exact templates, tool adapters, assets, generation workflows, risk formulas, and pipeline orchestration were excluded.

## SeaArt storyboard-prompt-assistant

- Source: https://github.com/seaartpublic/skills/tree/main/storyboard-prompt-assistant
- Reviewed commit: `a3edc17605d525b54b2a5f61a4800f2dd8dd8b30`
- License: MIT; copyright 2026 Seaart AI.
- Local use: the local storyboard, editing-rhythm and continuity references independently adopt explicit shot purpose, concrete camera language, start/end states, motivated changes and continuity checks. Product-specific prompt templates, negative prompts, generation modes, platform routing, and execution workflows were excluded.

## cutmap

- Source: https://github.com/xykong36/cutmap
- Reviewed commit: `4743a1ece5234e4bd733dd334e7fe34f04e73d3b`
- License: MIT; copyright 2026 Xiangyu Kong.
- Local use: the video skills independently account for low-contrast transitions and meaningful within-shot visual evolution rather than relying on one fixed scene threshold. No Python code, CLI behavior, algorithms, default thresholds, output pages, examples, or media assets were copied or executed.

## doocs/md

- Source: https://github.com/doocs/md
- Reviewed commit: `1c2c2f41396225892b3b3f0b5765b7d2f5d1b435`
- License: WTFPL v2; copyright 2025 Doocs.
- Local use: the article report is emitted as clean Markdown with mobile-friendly headings and a removable editor appendix so it can enter a WeChat Markdown formatting workflow. No editor code, styles, themes, assets, image-hosting logic, or deployment configuration were copied.

## wechat-article-writer

- Source: https://github.com/sammyteng/wechat-article-writer
- Reviewed commit: `ebea28e40daa8c470339d657c585e16557f91ff0`
- License: MIT; copyright 2026 sammyteng.
- Local use: the local article skill independently adopts a thesis-first outline, mobile-readable short paragraphs, editorial evidence, and a pre-publication checklist. Categorical moderation claims, hard-coded credentials and paths, browser injection, external research, account-specific style, publishing commands, and automatic calls to other skills were explicitly excluded.

## Scene Scribe (review only; no adoption)

- Source: https://github.com/seki2020/scene-scribe
- Reviewed commit: `e84d871387979918793537579412683039a1b11d`
- License: no repository license was present at the reviewed commit.
- Local use: none. The repository was reviewed only to compare storyboard deliverables; no code, text, templates, examples, or assets were copied or adapted.

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

## watch-skill

- Source: https://github.com/oxbshw/watch-skill
- Reviewed commit: `994ee7514c64a9ec4980eeabef789b5e10ea28be`
- License: MIT; copyright 2026 oxbshw.
- Local use: the opening-hook and continuity-quality reviews independently adopt bounded observation, visible change and on-screen-text review, evidence-backed creator feedback, and an explicit distinction between observation, risk and verified outcomes. The upstream runtime, scoring formulas, CLI, MCP, REST API, capture/index stores, OCR, ASR, model integrations, scripts, examples, tests, and assets were excluded.

## drama-skills

- Source: https://github.com/zenstory-ai/drama-skills
- Reviewed commit: `3ab6b8550bbccef71001d2187e2b2ac9a74ab917`
- License: MIT; copyright 2026 drama-skills contributors.
- Local use: the opening-hook review independently separates bounded evidence, viewer or production impact, and the required revision outcome. Upstream review wording, templates, rubrics, scripts, examples, production adapters, assets, generation workflow, and cross-Skill orchestration were excluded.

## video-shotcraft

- Source: https://github.com/Vincentwei1021/video-shotcraft
- Reviewed commit: `b0cb89173c9278042db78c3fb9c339814966f874`
- License: Apache-2.0; copyright 2026 Wei Yihao.
- Local use: the opening-hook review independently emphasizes reviewing rendered evidence before delivery, legible on-screen text, a clear initial subject, purposeful visual progression, and shot-specific handoff checks. Upstream wording, shot cards, recipes, demos, media, Remotion templates, source code, gallery, generation workflow, sound library, examples, and assets were excluded.

Updating any reviewed commit requires a fresh license and prompt-injection review, static fixtures, and real-provider E2E before release.
