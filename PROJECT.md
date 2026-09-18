# FrameFetch Server 项目说明

核对日期：2026-09-18。本文仅适用于 `video-server` 独立仓库，记录当前技术选型、目录和运行边界。协作与交付规则以 [AGENTS.md](AGENTS.md) 为准，运行入口以 [README.md](README.md) 为准，精确依赖版本以清单和锁文件为准。

## 1. 项目职责

本项目负责 FastAPI API、Next.js Web、媒体解析与下载、文档导入、制品管理、异步任务及 AI 分析，并包含独立发行的 Codex 插件。

Flutter App 是独立项目，通过 API 使用本项目能力，不在本仓库维护移动端实现或制定其工程规范。

## 2. 技术选型

### 服务端与基础服务

| 层次 | 当前选型 | 用途 |
| --- | --- | --- |
| 语言与依赖 | Python 3.12、uv、`uv.lock` | 后端运行时与可复现依赖 |
| HTTP API | FastAPI、Uvicorn、Pydantic / pydantic-settings | 路由、类型校验、配置与 OpenAPI |
| 数据访问 | PostgreSQL、SQLAlchemy 2 异步接口、asyncpg | 用户、任务、状态与业务数据 |
| 数据库结构 | `backend/sql/schema.sql` | 维护可重复执行的当前态结构，不维护迁移历史目录 |
| 消息处理 | RabbitMQ、aio-pika、Transactional Outbox | 可靠发布、异步消费与任务恢复 |
| 会话辅助存储 | Redis | 带 TTL 的认证状态与刷新凭据轮换等能力 |
| 制品存储 | MinIO | 视频、图片、文档和报告等对象 |
| 媒体执行 | yt-dlp、FFmpeg、ffprobe | 解析、下载、转封装及媒体文件校验 |
| 网络出口 | Squid 受控代理 | Runner 出口控制与私网访问隔离 |
| 文档处理 | python-docx、pypdf、markdown-it-py | DOCX、PDF、Markdown 等输入与报告处理 |
| AI 适配 | Codex App Server、Claude CLI、LangChain 及模型 API 适配器 | 在独立分析 Worker 中执行分析 |
| 部署 | Docker 多阶段镜像、Docker Compose | 同一生产镜像按服务启动不同进程 |
| 质量工具 | Ruff、mypy、pytest | 格式、静态类型及分层测试 |

依赖依据：[backend/pyproject.toml](backend/pyproject.toml)。yt-dlp 当前固定到指定上游提交；相关更新需要重新验证平台解析和真实媒体文件。

### Web

| 层次 | 当前选型 | 用途 |
| --- | --- | --- |
| 运行与语言 | Node.js 24、pnpm、TypeScript 5 | 构建与依赖管理 |
| 框架 | Next.js 16 App Router、React 19 | 页面、布局与 standalone 服务 |
| 设计系统 | Tailwind CSS 4、shadcn/ui、Radix UI | 主题、组件和可访问交互 |
| 图标与媒体 | Phosphor Icons、Vidstack | 统一功能图标与媒体播放 |
| API 请求 | Axios、OpenAPI 生成客户端 | 统一请求与接口类型 |
| 质量工具 | Biome、TypeScript、Vitest、Testing Library | 格式、类型和交互测试 |

依赖依据：[frontend/package.json](frontend/package.json)。`@umijs/openapi` 用于客户端生成；应用路由和页面由 Next.js 管理。视觉规范见 [design.md](design.md)，采用官方 Next.js、shadcn `radix-nova` / neutral / Phosphor 基线；页面使用无边框内容布局，控件保留官方实现。

## 3. 目录结构

以下为主要源码入口，省略依赖、缓存、构建产物和敏感运行数据。

```text
video-server/
├── AGENTS.md                      协作、架构和交付规范
├── README.md                      项目与运行入口
├── design.md                      Web 视觉规范
├── backend/
│   ├── pyproject.toml / uv.lock    Python 依赖与锁文件
│   ├── app/
│   │   ├── api/                   HTTP 路由、依赖和协议转换
│   │   ├── schemas/               请求与响应模型
│   │   ├── core/                  配置、安全和通用能力
│   │   ├── services/              业务用例与外部能力端口
│   │   ├── domain/                纯领域规则
│   │   ├── db/                    数据库连接、Session 与 Base
│   │   ├── models/                ORM 模型
│   │   ├── repositories/          查询、持久化与事务
│   │   ├── integrations/          存储、消息、AI 和媒体适配
│   │   ├── runner/                媒体执行与平台会话组件
│   │   ├── workers/               消费、调度和进程入口
│   │   ├── analysis_skills/       分析技能资源
│   │   ├── composition.py         服务装配
│   │   ├── runtime.py             类型化服务集合
│   │   ├── lifespan.py            运行资源生命周期
│   │   └── main.py                FastAPI 应用工厂
│   ├── egress/                    出口代理配置
│   ├── sql/schema.sql             当前数据库结构
│   └── tests/                     架构、契约、集成与单元测试
├── frontend/
│   ├── package.json               Web 依赖与脚本
│   ├── src/
│   │   ├── app/                   页面、布局与全局样式
│   │   ├── components/            按业务组织的组件及 ui 基础组件
│   │   ├── hooks/                 可复用状态与流程
│   │   ├── lib/                   请求封装、错误映射等基础设施
│   │   ├── api/                   OpenAPI 生成客户端
│   │   ├── types/                 业务类型
│   │   └── utils/                 通用函数
│   ├── public/                    静态资源
│   └── tests/                     Web 测试
├── plugins/framefetch/            Codex 插件、MCP 和独立 Local Agent
├── .agents/plugins/               仓库插件市场清单
├── docs/                          设计、需求、计划、验收与运维
├── Dockerfile                     统一生产镜像
├── docker-compose.yml            本机业务拓扑
├── docker-compose-prod.yml        生产业务拓扑
└── docker-compose-env.yml         GitHub CI 隔离基础服务夹具
```

后端依赖方向为 `api/workers → services → domain`。路由负责协议转换，服务组织业务用例，仓库管理查询与事务，领域层不依赖框架或基础设施。

前端页面位于 `src/app/`，业务组件按功能放在 `src/components/`，请求直接从 `src/api/` 生成代码导入，统一使用 `src/lib/request.ts` 的 Axios 封装；不建立平行路由或独立 `src/features/` 目录。视觉规范见 [design.md](design.md)，采用官方 Next.js、shadcn `radix-nova` / neutral / Phosphor 基线；页面使用无边框内容布局，控件保留官方实现。

## 4. 本地 Agent 与平台配置维护

当前存在不同职责的本地组件，维护时需要明确对应入口：

| 组件 | 代码入口 | 当前职责 |
| --- | --- | --- |
| FrameFetch Local Agent | `plugins/framefetch/scripts/framefetch_agent.py` | Codex/Claude Code 安装、登录诊断，以及本地 Agent 启停 |
| MCP 桥接 | `plugins/framefetch/scripts/framefetch_mcp.py` | 向 Codex 暴露 status、doctor、start、stop 工具 |
| Analysis Agent / Worker | `backend/app/workers/analysis/` | 宿主机分析服务管理与实际任务执行 |
| Provider Cookie Agent | `backend/app/runner/provider_cookie_agent.py` | 按平台处理受控会话请求与临时租约；macOS 使用按需队列服务 |
| 会话策略与安装 | `provider_session_policy.py`、`provider_session_setup.py`（位于 `runner/`） | 平台来源策略、来源安装及检查 |
| YouTube 会话维护器 | `backend/app/runner/provider_session_maintainer.py` | 独立维护 YouTube 会话文件，当前不负责所有平台 |

配置与运行边界：

- `.env` / `.env.prod` 保存部署配置，本地已有文件按现状复用；本文不记录密钥、Cookie 或 Token 值。
- 生产 YouTube、抖音、Reddit 使用各自只读会话来源；视频号按需使用专用元宝来源。具体配置以生产 Compose 与平台运维手册为准。
- `.provider-sessions/<provider>/` 属于本地敏感运行数据，不作为源码提交。来源目录可通过部署配置调整。
- Local Agent 的 CLI 登录诊断不代表 YouTube、抖音等媒体平台会话有效，也不代表分析任务已经完成。
- “统一多平台配置、状态检查与恢复入口”是当前讨论的改进方向，尚不能作为已经实现的全平台服务描述。现有 YouTube 维护器不能替代抖音等平台的独立恢复验证。
- 平台恢复需要分别验证元数据解析和真实媒体文件；进程存活或文件存在不足以证明恢复成功。

实现说明见 [插件 README](plugins/framefetch/README.md)、[YouTube 会话手册](docs/operations/002-YouTube受控会话运行手册.md)及[个人部署重启与换机手册](docs/operations/008-个人部署重启与换机手册.md)。

## 5. 运行与数据边界

- PostgreSQL 是业务与任务状态事实来源，Transactional Outbox 将消息发布意图持久化，再由独立发布进程投递 RabbitMQ。
- 下载、导入、报告和媒体命令由独立 Worker / Runner 执行；制品经过校验后写入 MinIO。
- AI 分析由独立宿主机 Analysis Worker 执行；分析失败不改变下载成功状态。
- OpenAPI 是 REST 契约来源；Web 使用生成客户端，实时事件使用 WebSocket，重连后以服务端状态收敛。
- Next.js 默认监听 `8101`，FastAPI 默认监听 `8111`。统一镜像按服务启动不同进程，FastAPI 不托管页面。
- 本机及生产 Compose 复用已有 PostgreSQL、RabbitMQ、Redis 和 MinIO；`docker-compose-env.yml` 仅作 GitHub CI 夹具。
- 数据库结构通过 `backend/sql/schema.sql` 维护当前态，不维护历史迁移目录。
- `.env`、会话数据、制品、日志和缓存不提交。镜像或配置更新按运维手册重新创建对应服务，普通 `restart` 不会应用这些变化。

## 6. 验证与文档维护

按改动范围执行最小充分验证：后端使用 Ruff、mypy、pytest；前端使用 Biome、类型检查、Vitest 与 Next.js build。接口变化审查 OpenAPI 和生成客户端；平台恢复需分别验证元数据与真实媒体文件。

功能文档按 Design → PRD → Plan → Acceptance 维护。本文不替代服务健康检查，也不表示各平台当前均可用。

详细入口：[文档索引](docs/README.md)、[后端说明](backend/README.md)、[前端说明](frontend/README.md)、[Compose 运维](docs/operations/001-root-compose运行手册.md)。
