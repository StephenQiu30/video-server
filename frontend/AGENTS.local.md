# AGENTS.local.md

本文件记录 `video-web` 的项目级边界；长期稳定规则以 `AGENTS.md` 为准。

## 当前项目规范

1. 本仓库只负责 Web；不得修改相邻的 `video-server` 或其他仓库。
2. 当前产品与技术事实以 `docs/design/archive/`、`docs/prd/archive/` 的 001–004 基线、活动 `docs/plans/` 和 `docs/acceptance/` 为准；不得恢复已清除旧设计或自行扩展范围。
3. 当前 MVP 仅包含“粘贴单个公开链接、选择分辨率、查看下载状态、获取文件”；Design/PRD 已归档，4 份 Plan 已实施，4 份 Acceptance 仍为 Blocked。
4. 服务端基础设施已经冻结为 PostgreSQL、RabbitMQ、MinIO；Web 只消费 FastAPI/OpenAPI 与 MinIO 预签名 URL，不提供任何基础设施切换入口。
5. 唯一交付链是 `Design → PRD → Plan → Acceptance`；执行必须满足 Design 中预先冻结的验收标准，任何下游文档不得降低标准或事后增加豁免。
6. 任何阶段开始前必须已有 `docs/acceptance/` 下对应的 `Defined` 验收文档，冻结阶段前置条件、逐任务验收、DAC/AC、验证命令和证据；实现完成后只能填写证据与结论，不得临时降低标准。
7. 项目角色放在 `.codex/agents/`，可复用流程放在 `.codex/skills/`。
8. 不维护 `.planning`、日记、临时进度文件、占位页面或重复治理目录。
9. AI 内容提取、字幕、播放列表、批量、账号、历史、私有媒体和 DRM 绕过均不属于当前 MVP；除非先更新并确认 Design，不得恢复相关旧文档或实现。
