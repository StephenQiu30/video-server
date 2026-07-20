# video-server

`video-server` 是万能视频下载器 MVP 的服务端仓库。

## 当前状态

- MVP 只覆盖：解析单个公开非 DRM 视频链接、返回分辨率选项、异步下载与文件获取。
- 4 份服务端 Design 与 4 份 PRD 已实现并归档，4 份 Plan 已实施。
- PostgreSQL、RabbitMQ、MinIO 是唯一基础设施选型，不保留候选方案或适配层。
- FastAPI API、下载 Worker、PostgreSQL、RabbitMQ、MinIO、Alembic、yt-dlp/FFmpeg 与测试代码已进入 `main`。
- 4 份 Acceptance 已执行但仍为 Blocked；未完成项以 [`docs/acceptance/README.md`](docs/acceptance/README.md) 为准。

## 重新设计门禁

后续工作固定遵循：

`Design → PRD → Plan → Acceptance`

当前 MVP 已实现。Design/PRD 基线位于归档目录；新增能力必须重新走完整交付链，现有未通过项只在对应 Acceptance 中补充证据与结论。

## 项目规范

本仓库按 [stephen-codex](https://github.com/StephenQiu30/stephen-codex) 当前 `main` 整理：

- `AGENTS.md`：长期协作、交付与 Git 规则。
- `AGENTS.local.md`：本仓库边界与重新设计门禁。
- `WORKFLOW.md`：Symphony/Linear 编排契约。
- `.codex/`：Agent 角色与核心流程。
- `docs/`：正式文档分类骨架。
- `.github/`：PR 模板与基础 CI。

文档入口见 [`docs/README.md`](docs/README.md)，运行配置模板见 [`.env.example`](.env.example)，本地编排见 [`compose.yml`](compose.yml)。
