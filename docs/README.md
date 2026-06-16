# 万能视频下载器项目文档入口

更新时间：2026-06-10

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

本项目已按 SDD 方式重建文档链路，采用“一个功能点一个 PRD”的方式组织需求，再把每个 PRD 拆成多个顺序编号的 Plan，最后映射到 Linear 父子 issue。

当前主线覆盖个人自部署万能视频下载器 MVP，并补充后端结构规范化扩展：

- `docs/prd/01-解析入口与URL安全.md` 到 `docs/prd/09-视频源可下载能力与中心化架构.md`
- `docs/design/01-个人自部署万能视频下载器技术设计.md`
- `docs/design/02-FastAPI后端结构重设计与规范化方案.md`
- `docs/plans/01-URL协议与地址安全计划.md` 到 `docs/plans/14-视频源可下载能力审计与中心化治理计划.md`
- `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`
- `docs/operations/01-个人自部署万能视频下载器运行与部署.md`

## 关键原则

1. 一个功能点一个 PRD，一个 PRD 可拆成多个 Plan。
2. 先完成 PRD、Design、Plan，再进入实现。
3. 下载能力只面向用户有权保存的公开或授权内容，不设计规避 DRM、付费墙、盗版传播或平台访问控制的能力。
4. 文档、规范、验收口径和 Linear issue 必须同步演进。

## 与 Claude 规范入口的关系

- `docs/` 负责项目事实、需求、方案、计划、验收和合规资料。
- `CLAUDE.md`、`CLAUDE.local.md`、`.claude/` 和 `WORKFLOW.md` 负责 Claude Agent 协作规范与 Symphony 编排。
- `openspec/` 负责长期行为与流程约束的 SDD 规范层。
