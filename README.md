# server

`server` 是万能视频下载器的统一服务仓库。前端源码、后端 API、Outbox、下载 Worker、宿主机 AI Worker 和运行编排在同一个仓库内维护。

## 目录

```text
server/
├── backend/       FastAPI、领域逻辑、Worker、当前态 SQL 与测试
├── frontend/      Next.js App Router、Radix UI、Tailwind CSS 前端与测试
├── docs/          当前 Design、PRD、Plan、Acceptance 与运维文档
├── Dockerfile
├── docker-compose.yml       本地完整服务拓扑（.env、宿主机端口）
└── docker-compose-prod.yml  生产环境覆盖（.env.prod、镜像与端口）
```

生产环境不运行独立的前端容器。根目录 `Dockerfile` 先构建 `frontend/`，再将静态产物复制到统一 Python 镜像，由 FastAPI 同源提供页面和 `/api/*` 接口。API 与下载 Worker 使用同一代码镜像；AI Worker 作为本机登录用户的宿主机进程运行，以复用 Codex 或 Claude CLI 的 OAuth 登录。

## 本地开发

前端要求 Node.js 24 LTS 与 npm 11.19，具体范围以 `frontend/package.json` 为准。

```bash
cd backend
uv sync --frozen --dev
uv run pytest -q

cd ../frontend
npm ci
npm run dev
```

前端开发服务器固定将 `/api/` 和 `/health/` 代理到 `http://127.0.0.1:8101`；生产构建使用相对 API 路径，不需要浏览器可见的后端地址。

## API 文档与客户端

API 启动后访问 `/docs` 查看 Swagger UI，访问 `/openapi.json` 获取 OpenAPI 契约。公共业务接口统一位于 `/api/*`，当前不维护没有实际兼容需求的版本目录或 `/api/v1` 前缀。

前端接口类型和请求方法完全由该契约生成，请求统一通过 Axios 封装：

```bash
cd frontend
npm run openapi
```

该命令直接使用 `@umijs/openapi` 和 `frontend/openapi2ts.config.ts` 读取 FastAPI 的 `/openapi.json`，更新 `frontend/src/services/video/`；生成代码通过 `frontend/src/lib/request.ts` 调用同源 Axios 实例。执行前需启动后端 API，可用 `OPENAPI_SCHEMA_URL` 临时覆盖契约地址。

管理员可从 `/admin/analytics` 查看 7、30 或 90 天的下载摘要、每日趋势和视频来源分布；数据由 `GET /api/admin/downloads/analytics` 从 PostgreSQL 聚合。原始 URL 仍只以密文包保存在解析记录中，统计响应不返回 URL、`owner_hash`、`provider_hints` 或 `error_message`。

## 视频源

Media Runner 通过版本化 Provider Profile 统一处理 YouTube、Bilibili、抖音、TikTok、小红书、Vimeo、X/Twitter、Instagram、Facebook、Twitch、Reddit、Pinterest、微博、优酷、腾讯视频、Dailymotion 和 NicoNico 等公开媒体链接；未登记的 HTTP(S) 地址继续交给无凭据的 yt-dlp Generic extractor。登记域名不等于已经验证，实际状态通过 `GET /api/providers` 查询。YouTube 可显式启用独立运维 Runner 的受控会话与 PO Token sidecar；普通请求仍不接受 Cookie，private、会员、购买和 DRM 内容仍会拒绝。

首页与 API 都支持只包含一个 HTTP(S) 链接的公开分享文案；首页会先提取链接，因此标题、话题和复制提示不会随请求发送。抖音公开单视频优先由随 Runner 交付的可信插件读取公开分享页，再进入原有格式选择、下载和制品校验链路；该能力不上传 Cookie、不生成平台签名，也不承诺无水印、原始母版或受限内容可用。

## 容器运行

根目录两份 Compose 按职责分层，不使用 `deploy/` 目录：Compose 启动 API、下载链路和基础设施，宿主机单独启动 AI Worker；生产文件只覆盖生产差异。

| 文件 | 用途 | 启动方式 |
| --- | --- | --- |
| `docker-compose.yml` | 本地 `.env`、API/下载拓扑、基础设施、健康检查和卷 | 启动本地基础环境 |
| `docker-compose-prod.yml` | 生产 `.env.prod`、生产镜像、容器名和对外端口 | 与基础配置组合 |

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.yml up -d --build

# 生产环境使用基础拓扑叠加生产差异
cp .env.prod.example .env.prod
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml up -d --build
```

本地 `docker-compose.yml` 负责本地环境插值、宿主机端口和完整服务拓扑，
`docker-compose-prod.yml` 负责生产环境校验、镜像和对外端口。Compose 使用带环境前缀的稳定容器名，
不会出现 `xxx-1` 这类副本后缀；生产覆盖会在 Compose 解析阶段校验关键变量。环境变量模板只维护在
`.env.example` 与 `.env.prod.example`；真实本地值放在被 Git 忽略的 `.env` 或
`.env.prod` 中。

API 的短窗口限流状态存放在独立 Valkey 服务；数据库、队列、配额、对象存储和 Runner RPC 使用独立内部网络，Media Runner 只接收 Runner HMAC 与受控出口代理配置。

AI 分析通过宿主机 Codex CLI 或 Claude CLI adapter 运行，不使用项目 API Key、本地 ASR 或本地模型。当前本机已验收的默认 Provider 是 Codex；启用 Claude 前必须确认实际模型路由能理解 Read 图片并通过真实视频 canary。先完成对应 CLI 登录，再从 `backend/` 启动 Worker：

```bash
cd backend
uv run python -m app.workers.analysis.main
```

Worker 会先验证 CLI、OAuth 登录、FFmpeg 与 FFprobe，再连接队列。应用把受限抽帧交给所选云端模型观察，因此这不是离线推理；视频容器不直接上传，但模型查看的帧会离开本机。本地与生产 API 默认开启 `ANALYSIS_ENABLED`；生产部署必须在同一宿主机持续运行已登录 OAuth 的 Worker，否则分析任务会保持排队状态。

服务入口默认为 <http://localhost:8101>。本地使用 `docker-compose.yml`，生产使用基础配置叠加 `docker-compose-prod.yml`。

当前架构依据见 [`docs/design/001-server单仓与运行时架构设计.md`](docs/design/001-server单仓与运行时架构设计.md) 与 [`docs/design/010-Codex与Claude CLI视频分析设计.md`](docs/design/010-Codex与Claude CLI视频分析设计.md)。数据库只保留 [`backend/sql/schema.sql`](backend/sql/schema.sql) 当前定义，新结构使用空数据卷初始化，不维护历史迁移和兼容分支。002 已通过受控直链 MP4 的真实下载闭环验收；010 的自动化与真实 CLI 验收状态以对应 Acceptance 文档为准。

## 贡献与提交

项目结构、架构边界和质量门禁见 [`AGENTS.md`](AGENTS.md)，贡献流程见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。每个可独立验证的小任务使用 Conventional Commits 格式和中文描述提交，例如 `feat(api): 增加下载任务取消接口`；不需要作用域时写成 `feat: 增加功能`，不要使用空作用域 `feat(): ...`。首次克隆后可按贡献指南启用仓库提交模板与本地校验钩子，CI 也会检查新增提交。
