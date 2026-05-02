## Context

项目已确认 M1 技术栈：React + Umi + Ant Design Pro、FastAPI + Python 3.12、yt-dlp + FFmpeg、RQ + Redis、PostgreSQL、MinIO / S3、JWT 用户系统、Docker Compose。当前仓库尚未有应用代码，M1 的核心任务是建立可运行骨架和最小下载闭环边界。

## Goals / Non-Goals

**Goals:**

- 建立默认推荐的 monorepo 目录：`apps/web`、`apps/api`、`apps/worker`、`packages/shared`、`infra/docker`。
- 建立 Ant Design Pro / Umi 前端工作台，覆盖注册、登录、链接输入、任务台和任务详情入口。
- 建立 FastAPI 后端，覆盖 JWT 鉴权、任务 API、解析 API、文件访问授权。
- 建立 RQ Worker，后台执行 yt-dlp 下载和 FFmpeg 合并。
- 建立本地开发运行基线，默认复用已有 Python、PostgreSQL、Redis、MinIO / S3 服务。
- 保留 Docker Compose 作为上线部署或隔离运行方案。
- 固化默认资源限制：单任务最大 2GB、最长 2 小时、全局并发 2、单用户并发 1、文件保留 24 小时。
- 使用私有 MinIO bucket 和短期预签名 URL 交付文件。

**Non-Goals:**

- 不实现 AI 摘要、问答、思维导图。
- 不实现支付、会员、团队/组织权限。
- 不托管用户平台 Cookie。
- 不实现 B 站、抖音等平台专用解析。
- 不实现大规模批量抓取和频道订阅。

## Decisions

1. **前端采用 Ant Design Pro / Umi**

   用户已明确选择 Ant Design Pro/Umi。M1 使用 Umi + Ant Design Pro 体系初始化 `apps/web`，优先复用 ProLayout、ProTable、ProForm 和登录页模式，避免在 React + Vite 下手动拼装 Pro 体验。

2. **默认项目结构采用轻量 monorepo**

   使用 `apps/web`、`apps/api`、`apps/worker`、`packages/shared`、`infra/docker`。这样前端、API、Worker、共享契约和部署配置边界清晰，后续可以独立扩展。

3. **JWT 允许注册**

   M1 提供注册、登录、当前用户查询和任务归属。首版不做团队权限、邀请码、邮箱验证和第三方 OAuth。

4. **MinIO 使用成熟私有 bucket + 预签名 URL 模式**

   bucket 默认私有，后端负责生成短期预签名下载 URL。对象 key 使用 `users/{user_id}/tasks/{task_id}/{filename}`，避免暴露公共桶和内部对象路径。

5. **资源限制使用保守默认值**

   单任务最大 2GB、最长 2 小时、全局并发 2、单用户并发 1、文件保留 24 小时。所有值通过环境变量配置，默认值写入 `.env.example`。

6. **OpenSpec 管理 M1 实现变更**

   M1 的实现、任务拆分和验收以 `bootstrap-mvp-foundation` 变更为准。实现后必须更新 tasks 并通过 `openspec validate --all`。

## Risks / Trade-offs

- [Risk] Ant Design Pro/Umi 相比 Vite 更重 → Mitigation：M1 只启用布局、登录、表单、表格和基础路由，不引入过多插件。
- [Risk] 服务端下载大文件占用带宽、CPU 和磁盘 → Mitigation：默认限制文件大小、运行时长、并发和保留时间。
- [Risk] yt-dlp 平台规则变化导致解析失败 → Mitigation：失败原因分类展示，并保留内核升级路径。
- [Risk] JWT 注册开放后可能被滥用 → Mitigation：M1 保留注册入口，但本地默认部署；公网部署前必须启用限流和任务配额。
- [Risk] MinIO 预签名 URL 泄露后短期可访问 → Mitigation：URL TTL 默认 15 分钟，bucket 保持私有，文件 24 小时后清理。

## Migration Plan

1. 创建 monorepo 目录和基础 README。
2. 初始化 `apps/web`、`apps/api`、`apps/worker`。
3. 配置本地开发脚本启动 API 和 Worker，复用本地 PostgreSQL、Redis、MinIO / S3。
4. 保留 Docker Compose 启动 PostgreSQL、Redis、MinIO、API、Worker，并作为部署路径。
5. 实现 JWT 用户系统和任务归属。
6. 实现解析、任务、下载、对象存储交付 API。
7. 完成验收样例和 OpenSpec 任务勾选。

## Open Questions

- M1 默认值已按保守方案确定；如项目负责人后续调整下载大小、并发或保留时间，需要更新 ADR 和环境变量默认值。
