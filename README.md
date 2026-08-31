<div align="center">
  <img src="frontend/public/logo.png" alt="帧取 FrameFetch 开源媒体工作流 Logo" width="88" />
  <h1>帧取 · FrameFetch</h1>
  <p><strong>开源、自托管的公开视频下载、剧本文档处理与 AI 分析工作流</strong></p>
  <p><em>Open-source, self-hosted media download, screenplay processing and AI video analysis workflow.</em></p>
  <p>
    <a href="https://github.com/StephenQiu30/video-server/actions/workflows/ci.yml"><img src="https://github.com/StephenQiu30/video-server/actions/workflows/ci.yml/badge.svg" alt="Required CI 状态" /></a>
    <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-111111.svg" alt="MIT License" /></a>
    <img src="https://img.shields.io/badge/Python-3.12-3776AB.svg" alt="Python 3.12" />
    <img src="https://img.shields.io/badge/Next.js-16-000000.svg" alt="Next.js 16" />
    <img src="https://img.shields.io/badge/Docker-Compose-2496ED.svg" alt="Docker Compose" />
  </p>
  <p>
    <a href="#快速开始">快速开始</a> ·
    <a href="#产品能力">产品能力</a> ·
    <a href="#界面预览">界面预览</a> ·
    <a href="#架构">架构</a> ·
    <a href="README.en.md">English</a>
  </p>
</div>

![帧取 FrameFetch 开源自托管视频工作流公开落地页](docs/images/landing.png)

> 截图由 `agent-browser` 在本地预览环境中采集；涉及媒体的界面使用仓库自带视觉回归素材，所有图片均不包含真实用户数据、凭据或第三方图片热链。采集说明见 [`docs/images/README.md`](docs/images/README.md)。

## 帧取是什么

帧取（FrameFetch）是一个面向创作者、内容研究者和开发者的开源媒体工作流。它把公开媒体链接或本地剧本文档转换为可观察、可恢复的异步任务：解析来源、选择真实格式、隔离下载与校验、保存制品，并按需生成结构化 AI 分析报告。

项目不是规避平台限制的下载脚本。默认能力只处理用户有权使用、公开、免费且非 DRM 的 HTTP(S) 内容；受保护、会员、私密、购买或地域限制内容不属于项目目标。

**English summary:** FrameFetch is an open-source, self-hosted video downloader and media workflow for authorized public content. It combines FastAPI, Next.js, PostgreSQL, RabbitMQ, MinIO, yt-dlp/FFmpeg adapters, screenplay ingestion and optional AI video analysis. See the [English README](README.en.md) for the complete overview.

## 产品能力

| 能力 | 当前实现 |
| --- | --- |
| 公开媒体解析 | 从公开链接或单链接分享文案中识别来源、媒体信息和真实可用格式 |
| 可靠异步下载 | API → Transactional Outbox → RabbitMQ → Download Worker → 隔离 Media Runner |
| 制品校验与存储 | 通过重新解析、语义格式校验、FFmpeg/ffprobe、大小、时长和 SHA-256 校验后写入 MinIO |
| 实时任务状态 | WebSocket 增量事件、版本检查、断线重连与 resync；实时连接不作为任务事实源 |
| 剧本文档工作流 | 导入 Markdown、Fountain、TXT、PDF、DOCX，提供阅读、目录、分页和分析入口 |
| 可选 AI 分析 | 宿主机 Codex Agent 或管理员配置的模型 Provider；报告可导出 Markdown/DOCX |
| 运维与管理 | 用户与角色、Provider 状态、下载分析、持久文件分页和显式清理 |
| 原生移动端 | 独立的 [FrameFetch Flutter iOS/Android 客户端](https://github.com/StephenQiu30/video-app) |

### 为什么采用工作流架构

- **可恢复**：PostgreSQL 保存任务事实，Transactional Outbox 保证数据库状态与消息意图一致。
- **可隔离**：下载、媒体命令和 AI 长任务不在 HTTP 请求进程中执行；Runner 经过受控出口代理。
- **可验证**：Provider 返回值不会直接成为最终制品，Worker 会重新解析并验证媒体身份、格式和文件完整性。
- **可扩展**：Provider、Runner、应用用例、OpenAPI 客户端和前端 feature 组件保持清晰边界。
- **可自托管**：Docker Compose 分离基础环境、业务服务和生产差异，不依赖官方托管服务。

## 界面预览

![帧取 FrameFetch 登录后的公开媒体解析、视频格式选择与异步下载工作区](docs/images/home.png)

<p align="center"><strong>登录后的媒体解析与真实格式选择工作区</strong></p>

<table>
  <tr>
    <td width="50%"><img src="docs/images/providers.png" alt="帧取 FrameFetch 平台 Provider 能力与最近验证状态页面" /></td>
    <td width="50%"><img src="docs/images/login.png" alt="帧取 FrameFetch 账户登录与安全会话页面" /></td>
  </tr>
  <tr>
    <td align="center"><strong>Provider 能力与验证状态</strong></td>
    <td align="center"><strong>账户登录与安全会话</strong></td>
  </tr>
</table>

主要 Web 路由包括媒体解析与下载、任务历史与详情、剧本文档阅读与分析、Provider 状态、账户设置，以及管理员用户、文件、分析和 AI Provider 管理。实际可用平台和状态以部署实例的 `/providers` 页面与 canary 结果为准。

## 快速开始

### 前置条件

- Docker Engine 与 Docker Compose
- 为媒体制品、数据库和消息服务预留足够的磁盘空间与运行资源
- 用于生产部署时，需要自行提供强随机密钥和公开访问地址

### Docker Compose 启动

```bash
git clone https://github.com/StephenQiu30/video-server.git
cd video-server
cp .env.example .env

# 启动项目专用的 PostgreSQL、RabbitMQ、Valkey 与 MinIO
docker compose --env-file .env -f docker-compose-env.yml up -d

# 启动 Web、API、Worker、Runner 与受控出口代理
docker compose --env-file .env -f docker-compose.yml \
  up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
```

PowerShell 使用相同入口：

```powershell
Copy-Item .env.example .env
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
```

启动后访问：

- Web 应用：<http://localhost:8101>
- Swagger UI：<http://localhost:8111/docs>
- OpenAPI：<http://localhost:8111/openapi.json>

健康检查：

```bash
curl --fail http://127.0.0.1:8111/health/live
curl --fail http://127.0.0.1:8111/health/ready
curl --fail --head http://127.0.0.1:8101/
```

只需要下载与剧本文档导入时，可在 `.env` 中设置 `ANALYSIS_ENABLED=false`。完整的启动、停止、已有基础环境复用和故障恢复方式见 [Compose 运行手册](docs/operations/001-root-compose运行手册.md)。更新代码时先执行 `git pull --ff-only`，再重新运行上面的业务 `up` 命令；`docker compose restart` 不会应用新镜像或环境配置。

### 启用 AI 分析

AI Worker 独立运行，不包含在业务 Compose 中。默认线路可以复用宿主机已登录的 Codex App Server；管理员也可在 Web 中配置受支持的模型 Provider。宿主机 Agent 的统一管理入口为：

```bash
cd backend
uv sync --frozen --dev
uv run python -m app.workers.analysis.agent_cli doctor
uv run python -m app.workers.analysis.agent_cli install
uv run python -m app.workers.analysis.agent_cli status
```

不要把 Codex/Claude OAuth 目录复制或挂载进容器。启用第三方模型前，请使用已获授权样本完成 canary，并确认模型服务条款和组织数据策略。

## 架构

```mermaid
flowchart LR
  Browser[Web / Mobile Client] --> Frontend[Next.js :8101]
  Frontend --> API[FastAPI :8111]
  API --> DB[(PostgreSQL)]
  DB --> Outbox[Transactional Outbox]
  Outbox --> MQ[RabbitMQ]
  MQ --> Download[Download Worker]
  MQ --> Documents[Import / Report Workers]
  Download --> Runner[Isolated Media Runner]
  Runner --> Proxy[Controlled Egress Proxy]
  Download --> Storage[(MinIO)]
  Documents --> Storage
  HostAI[Host AI Agent] --> MQ
  HostAI --> Storage
  API -. WebSocket events .-> Browser
```

| 层 | 技术 |
| --- | --- |
| Frontend | Next.js 16、React 19、TypeScript、Tailwind CSS、Radix UI |
| Backend | Python 3.12、FastAPI、SQLAlchemy、PostgreSQL |
| Async | Transactional Outbox、RabbitMQ、Valkey、幂等 Worker 与 lease/heartbeat |
| Media | FFmpeg、ffprobe、yt-dlp 适配层、隔离 Runner、Squid egress proxy |
| Storage | MinIO 对象存储与短时预签名访问地址 |
| Contract | OpenAPI 是 Web、Flutter 与服务端之间的唯一接口契约 |

详细的产品、设计、研究、验收和运维事实收录在 [文档索引](docs/README.md)。

## 安全与合规边界

- 只处理你拥有相应权利的内容，并遵守内容来源、所在地和部署环境适用的法律与平台规则。
- 匿名 Provider 只接受公开、免费、非 DRM 的 HTTP(S) 内容；私网 URL、任意 yt-dlp 参数和 shell 输入始终禁止。
- 普通业务请求不接收原始 Cookie。Provider 凭据仅进入对应的只读、隔离 Runner，不进入浏览器、普通日志或其他 Worker。
- Edge Agent 只能传输用户已合法取得并明确选择的明文文件，不能读取平台会话、拦截流量、提取密钥或转换受保护媒体。
- 外部媒体访问必须经过阻断私网的出口代理；入口 URL 校验不能替代网络隔离。

发现安全问题时，请不要在公开 Issue 中披露利用细节、密钥或用户内容；按 [安全策略](SECURITY.md) 使用私有渠道报告。

## 当前限制

- 项目仍在持续演进，目前提供自托管源码和 Compose 运行方式，不承诺官方 SaaS、公共演示站或服务可用性 SLA。
- Provider 能力受来源页面和平台变化影响；平台名称不代表对所有内容、地区或账户权益都可用。
- AI 分析依赖独立宿主机 Agent 或部署方配置的模型服务，关闭 AI 不影响下载和文档导入。
- 预签名 URL 会过期，但最终制品不会因此自动删除；管理员仍需规划 MinIO 容量、备份和显式清理策略。
- 对外部署前必须替换 `.env.prod.example` 中的占位凭据，并完成网络、存储、Runner 和 Provider canary 验收。

## 本地开发

前端需要 Node.js `>=24.15 <25` 与 npm 11，后端需要 Python `>=3.12 <3.13` 与 [uv](https://docs.astral.sh/uv/)。代码级质量门禁：

```bash
cd backend
uv sync --frozen --dev
uv run --frozen ruff check app tests
uv run --frozen mypy --strict app
uv run --frozen pytest -q

cd ../frontend
npm ci
npm run lint
npm test
npm run build
```

仓库主要目录：

```text
backend/                 FastAPI、领域逻辑、Worker、Runner 与当前态 SQL
frontend/                Next.js App Router、业务组件、Hooks 与 OpenAPI 客户端
docs/                    设计、需求、计划、验收、研究和运维事实
Dockerfile               前后端统一生产镜像
docker-compose-env.yml   PostgreSQL、RabbitMQ、Valkey、MinIO 基础环境
docker-compose.yml       Web、API、Worker、Runner 与出口代理
docker-compose-prod.yml  生产业务差异
```

## 参与贡献

欢迎通过 Issue 或 Pull Request 参与 Provider 适配、可靠性、前端与移动端体验、AI 报告、测试和文档建设。开始前请阅读：

- [贡献指南](CONTRIBUTING.md)
- [社区行为准则](CODE_OF_CONDUCT.md)
- [仓库协作规范](AGENTS.md)
- [文档索引](docs/README.md)
- [安全策略](SECURITY.md)

提交变更时，请保持实现、OpenAPI 契约、测试、运行手册和验收证据一致，并只提交小而完整、可独立验证的改动。

## 许可证

FrameFetch 基于 [MIT License](LICENSE) 开源。MIT 许可证授予软件使用、修改和分发权，不代表授予任何第三方媒体内容的下载、复制或分析权。
