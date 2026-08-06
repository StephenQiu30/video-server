# video-web

`video-web` 是万能视频下载器 MVP 的 Web 仓库。

## 当前状态

- MVP 只覆盖：粘贴单个公开视频链接、选择分辨率、查看任务状态和获取文件。
- 4 份 Web Design 与 4 份 PRD 已完成文档生命周期并归档，4 份 Plan 已实施。
- Web 固定消费 PostgreSQL/RabbitMQ/MinIO 后端架构提供的 FastAPI/OpenAPI 契约，不提供基础设施选择。
- 标准 Ant Design Pro/Umi 工程、OpenAPI 生成 Service、下载交互与测试代码已进入 `main`。
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

文档入口见 [`docs/README.md`](docs/README.md)。本地开发使用 `npm ci` 后执行 `npm run dev`；质量门禁见 [`package.json`](package.json) scripts。容器默认环境和 `prod` 覆盖分别由 [`docker-compose.yml`](docker-compose.yml) 与 [`docker-compose-prod.yml`](docker-compose-prod.yml) 提供，镜像继续使用标准 Ant Design Pro/Umi 构建流程，部署命令见 [`docs/operations/001-Docker部署操作.md`](docs/operations/001-Docker部署操作.md)。
