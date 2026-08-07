# server

`server` 是万能视频下载器的统一服务仓库。前端源码、后端 API、Outbox、下载 Worker、AI Worker 和运行编排在同一个仓库内维护，并通过同一个生产镜像交付。

## 目录

```text
server/
├── backend/       FastAPI、领域逻辑、Worker、当前态 SQL 与测试
├── frontend/      Ant Design Pro / Umi Max Web 源码、组件与测试
├── docs/          当前 Design、PRD、Plan、Acceptance 与运维文档
├── Dockerfile
├── docker-compose.yml       本地完整服务拓扑（.env、宿主机端口）
└── docker-compose-prod.yml  生产环境覆盖（.env.prod、镜像与端口）
```

生产环境不运行独立的前端容器。根目录 `Dockerfile` 先构建 `frontend/`，再将静态产物复制到统一 Python 镜像，由 FastAPI 同源提供页面和 `/api/*` 接口。API、下载 Worker 和 AI Worker 使用同一代码镜像、不同进程入口。

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

前端 API 客户端完全由该契约生成，不手工维护接口类型或请求函数：

```bash
cd frontend
npm run openapi
```

该命令使用 Umi Max OpenAPI 插件直接读取 FastAPI 的 `/openapi.json`，并更新 `frontend/src/services/video/`；执行前需启动后端 API。

## 视频源

Media Runner 通过可注册的 Provider Strategy 统一处理 YouTube、Bilibili、抖音、TikTok、Vimeo、X/Twitter、Instagram、Facebook、Twitch、Reddit、Pinterest、微博、优酷、腾讯视频、Dailymotion 和 NicoNico 等公开媒体链接；未登记的 HTTP(S) 地址继续交给 yt-dlp 的 Generic extractor。平台规则会变化，且登录、Cookie、DRM 或平台访问验证不在服务边界内，最终是否可下载以实际解析结果为准。

首页输入框也支持直接粘贴抖音分享文案；系统只提取其中唯一的 HTTP(S) 链接，标题、话题和复制提示不会发送到后端。若抖音要求新鲜浏览器会话，页面会显示平台访问提示，不会上传 Cookie 或绕过验证。

## 容器运行

根目录两份 Compose 按职责分层，不使用 `deploy/` 目录：本地文件可独立启动完整服务，生产文件只覆盖生产差异。

| 文件 | 用途 | 启动方式 |
| --- | --- | --- |
| `docker-compose.yml` | 本地 `.env`、宿主机端口、完整服务拓扑、健康检查、依赖关系和卷 | 可直接部署本地环境 |
| `docker-compose-prod.yml` | 生产 `.env.prod`、生产镜像、容器名和对外端口 | 与基础配置组合 |

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.yml up -d --build

# 生产环境使用基础拓扑叠加生产差异
cp .env.prod.example .env.prod
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml up -d --build
```

本地 `docker-compose.yml` 负责本地 `env_file`、宿主机端口和完整服务拓扑，
`docker-compose-prod.yml` 负责生产 `env_file`、镜像和容器名。Compose 使用带环境前缀的稳定容器名，
不会出现 `xxx-1` 这类副本后缀；生产覆盖会在 Compose 解析阶段校验关键变量。环境变量模板只维护在
`.env.example` 与 `.env.prod.example`；真实本地值放在被 Git 忽略的 `.env` 或
`.env.prod` 中。

LLM 默认通过 LangChain 连接宿主机已有的 Ollama 服务与 `qwen3:latest`；项目不安装 Ollama 或拉取模型。切换 DeepSeek 云端时设置 `ANALYSIS_PROVIDER=deepseek` 与 `DEEPSEEK_API_KEY`。音频转录仍使用独立 ASR 配置，真实视频分析需要 `OPENAI_API_KEY`。

Docker 本地开发时，`OLLAMA_BASE_URL` 默认使用 `http://host.docker.internal:11434`，因此 Ollama 必须监听容器可达的宿主机地址（不能只监听 `127.0.0.1`）。若直接在宿主机运行 analysis worker，可将其覆盖为 `http://localhost:11434`；Windows 上可在启动 Ollama 前设置 `OLLAMA_HOST=0.0.0.0:11434`。

服务入口默认为 <http://localhost:8101>。本地使用 `docker-compose.yml`，生产使用基础配置叠加 `docker-compose-prod.yml`。

当前架构依据见 [`docs/design/001-server单仓与运行时架构设计.md`](docs/design/001-server单仓与运行时架构设计.md)。数据库只保留 [`backend/sql/schema.sql`](backend/sql/schema.sql) 当前定义，新结构使用空数据卷初始化，不维护历史迁移和兼容分支。002 已通过受控直链 MP4 的真实 PostgreSQL/RabbitMQ/MinIO/yt-dlp/FFmpeg 与浏览器 MVP 核心验收，并通过一个 MediaTrack 公共审片链接的真实解析、HLS 下载与 ffprobe 校验，但不代表第三方站点矩阵均已覆盖；003 的真实 ASR + DeepSeek/Ollama E2E 尚未执行，仍保持 Pending。本轮已在宿主机 Ollama 的 `qwen3:latest` 上通过 LangChain 结构化分析冒烟；完整 ASR + 视频端到端仍待真实 OpenAI Key 与视频样本。

## 贡献与提交

项目结构、架构边界和质量门禁见 [`AGENTS.md`](AGENTS.md)，贡献流程见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。每个可独立验证的小任务使用 Conventional Commits 格式和中文描述提交，例如 `feat(api): 增加下载任务取消接口`；不需要作用域时写成 `feat: 增加功能`，不要使用空作用域 `feat(): ...`。
