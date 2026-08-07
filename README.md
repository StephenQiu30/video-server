# server

`server` 是万能视频下载器的统一服务仓库。前端源码、后端 API、Outbox、下载 Worker、AI Worker 和运行编排在同一个仓库内维护，并通过同一个生产镜像交付。

## 目录

```text
server/
├── backend/       FastAPI、领域逻辑、Worker、当前态 SQL 与测试
├── frontend/      Ant Design Pro / Umi Max Web 源码、组件与测试
├── docs/          当前 Design、PRD、Plan、Acceptance 与运维文档
├── Dockerfile
├── docker-compose.yml       本地应用环境（前后端及运行进程）
├── docker-compose-env.yml   本地基础设施环境
└── docker-compose-prod.yml  生产应用环境（前后端及运行进程）
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

## 容器运行

根目录三份 Compose 是三个可以独立执行的入口，不使用 `deploy/` 目录，也不通过文件叠加启动：

| 文件 | 用途 | 启动方式 |
| --- | --- | --- |
| `docker-compose.yml` | 本机 API 同源前端、Worker、Runner 与 egress proxy | 单独使用 |
| `docker-compose-env.yml` | 本机 PostgreSQL、RabbitMQ、MinIO 及初始化器 | 单独使用 |
| `docker-compose-prod.yml` | 线上 API 同源前端、Worker、Runner 与 egress proxy | 单独使用 |

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose -f docker-compose.yml up -d --build

# 生产环境只启动生产应用栈，不叠加本地文件
cp .env.prod.example .env.prod
docker compose --env-file .env.prod -f docker-compose-prod.yml up -d --build
```

三个 Compose 文件互不引用服务、卷、网络或覆盖配置。应用栈通过 `.env` 或
`.env.prod` 访问外部基础设施；本地环境栈通过 `.env` 中的
`POSTGRES_HOST_PORT`、`RABBITMQ_HOST_PORT`、`MINIO_HOST_PORT` 等变量发布宿主机端口。
Compose 使用带环境前缀的稳定容器名，不会出现 `xxx-1` 这类副本后缀。环境变量模板只维护在
`.env.example` 与 `.env.prod.example`；真实本地值放在被 Git 忽略的 `.env` 或
`.env.prod` 中。Compose 文件只负责引用 env 文件和声明编排关系。

LLM 默认通过 LangChain 连接宿主机已有的 Ollama 服务与 `deepseek-r1:8b`；项目不安装 Ollama 或拉取模型。切换 DeepSeek 云端时设置 `ANALYSIS_PROVIDER=deepseek` 与 `DEEPSEEK_API_KEY`。音频转录仍使用独立 ASR 配置，真实视频分析需要 `OPENAI_API_KEY`。

服务入口默认为 <http://localhost:8101>。本地应用和生产应用分别使用自己的 Compose 文件；基础设施单独使用 `docker-compose-env.yml`。

当前架构依据见 [`docs/design/001-server单仓与运行时架构设计.md`](docs/design/001-server单仓与运行时架构设计.md)。数据库只保留 [`backend/sql/schema.sql`](backend/sql/schema.sql) 当前定义，新结构使用空数据卷初始化，不维护历史迁移和兼容分支。002 已通过受控直链 MP4 的真实 PostgreSQL/RabbitMQ/MinIO/yt-dlp/FFmpeg 与浏览器 MVP 核心验收，并通过一个 MediaTrack 公共审片链接的真实解析、HLS 下载与 ffprobe 校验，但不代表第三方站点矩阵均已覆盖；003 的真实 ASR + DeepSeek/Ollama E2E 尚未执行，仍保持 Pending。

## 贡献与提交

项目结构、架构边界和质量门禁见 [`AGENTS.md`](AGENTS.md)，贡献流程见 [`CONTRIBUTING.md`](CONTRIBUTING.md)。每个可独立验证的小任务使用 Conventional Commits 格式和中文描述提交，例如 `feat(api): 增加下载任务取消接口`；不需要作用域时写成 `feat: 增加功能`，不要使用空作用域 `feat(): ...`。
