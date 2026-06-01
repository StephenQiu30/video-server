# 万能视频下载器项目文档入口

更新时间：2026-06-02

## 文档结构

文档按长期用途进入固定目录：

| 目录 | 用途 |
| --- | --- |
| `docs/prd/` | 产品需求、用户故事、MVP 边界和不做事项 |
| `docs/plans/` | 执行计划、阶段拆解、任务顺序和 Linear 映射 |
| `docs/design/` | 技术方案、架构决策、接口和数据结构 |
| `docs/acceptance/` | 验收标准、测试计划、验证记录和残余风险 |
| `docs/operations/` | 发布、部署、OpenAPI 协作、Git/PR 和运维规则 |

正式文档必须使用 `docs/TEMPLATE.md` 的 YAML frontmatter，至少说明 `layer`、`doc_no`、`audience`、`purpose`、`owner`、`inputs`、`outputs`、`triggers` 和 `downstream`。


## 当前状态

本项目已完成规范化 docs 目录治理，并按 PRD -> Plan -> Acceptance/Test Plan 的链路拆解万能视频下载器 MVP。当前 MVP 通过 Linear 项目 `Video Server 万能视频下载器 MVP` 管理 PRD 父 issue 和 Plan 子 issue。

## 关键原则

1. 先完成合规边界、产品范围与技术选型确认，再进入工程实现。
2. 参考成熟开源项目能力，但不照搬其商业、合规、支付与账号体系设计。
3. 下载能力只面向用户有权保存的公开或授权内容，不设计规避 DRM、付费墙、盗版传播或平台访问控制的能力。
4. 文档、规范、角色分工与验收口径必须和代码实现同步演进。

## 与多 Agent 规范入口的关系

- `docs/` 负责项目事实、需求、方案、计划、验收和合规资料。
- `AGENTS.md`、`AGENTS.local.md`、`.codex/agents/` 和 `.codex/skills/` 负责 Codex 入口。
- `CLAUDE.md`、`CLAUDE.local.md`、`.claude/agents/` 和 `.claude/skills/` 负责 Claude 入口。
- `CURSOR.md`、`CURSOR.local.md`、`.cursor/agents/`、`.cursor/skills/` 和 `.cursor/rules/` 负责 Cursor 入口。
- 三套入口应表达同一组项目约束，只按工具识别方式拆分，不互相替代。
