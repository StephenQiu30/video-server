# Backend

FastAPI API、下载/分析领域逻辑、异步 Worker、当前态数据库 SQL 和 Python 测试位于本模块。

所有 Python 与 `uv` 命令都应从 `backend/` 执行。数据库当前结构定义在可重复执行的 `sql/schema.sql`；宿主机或外部平台必须在启动业务容器前幂等加载该文件。项目不维护迁移历史、Compose 数据库初始化服务或旧 schema 兼容路径。生产镜像由仓库根目录 `Dockerfile` 统一构建。

## 目录约定

```text
app/
├── api/              FastAPI 装配、健康检查与 HTTP 契约
│   ├── routes/       `/api/*` 路由
│   └── schemas/      请求与响应模型
├── application/      用例编排与外部能力端口
├── domain/           不依赖框架的领域规则
├── infrastructure/   数据库、消息、对象存储和模型适配器
├── runner/           匿名或单 Provider 会话隔离的媒体执行进程
├── workers/          Outbox、下载和分析进程入口
├── composition.py    运行时依赖装配
└── main.py           FastAPI 进程入口
```

依赖方向保持为 `api/workers → application → domain`。FastAPI DTO 位于 `api/schemas/`；不要把数据库模型、Provider SDK 或 Worker 实现移入 `domain`。

公共接口不维护无实际兼容需求的版本目录或 URL 前缀。服务启动后可通过 `/docs` 访问 Swagger UI，通过 `/openapi.json` 获取供前端生成客户端的 OpenAPI 契约。

业务接口要求邮箱账户登录，注册时同时设置唯一用户名。密码使用 Argon2 哈希；短期 Access JWT 与可轮换、可撤销的 Refresh JWT 通过 `HttpOnly` Cookie 维护。JWT 密钥、签发方、受众、Cookie 名、有效期和初始管理员邮箱从根目录 `.env` 的 `AUTH_*` 配置读取，原始 Refresh JWT 不写入数据库。角色和启用状态以 PostgreSQL 为准，管理员可通过 `/api/admin/users` 管理账号，并通过 `/api/admin/providers` 维护平台状态目录的名称、排序与可见性。平台目录不控制域名匹配、Extractor、Runner 参数或会话能力。

Media Runner 通过 `app/runner/plugins/yt_dlp_plugins/` 加载随项目交付的可信站点提取器。MediaTrack 适配仅处理无需登录的公开审片视频和 API 明确授权的播放转码；抖音适配用数字视频 ID 构造固定公开分享页，快手适配把公开作品规范化到第一方移动分享页并限制短链重定向域。三者都继续经过受控代理、作品身份校验、大小/时长限制、重新 inspect、FFmpeg 和 ffprobe 校验，不使用 YouTube 运维 Cookie，不支持图集截断、账号内容、无水印承诺或原文件权限绕过。

主流视频源通过 `app/runner/provider_registry.py` 与 `app/runner/provider_catalog.py` 采用版本化 Profile + Registry 统一匹配；`provider_urls.py` 只保留兼容入口，未知站点使用无凭据的 yt-dlp Generic extractor。新增平台应先确认 extractor，再补 Profile、能力状态、错误 marker 与 metadata + Range canary。YouTube 运维会话只在独立 Runner 中从只读 Secret 建立操作级 `0600` Cookie jar；匿名与其他 Provider 命令不携带 Cookie。平台出口信誉需要隔离时，由运维使用 `RUNNER_PROVIDER_EGRESS_PROXIES` 按稳定 key 指向受控内部代理。

视觉分析通过宿主机 `codex exec` 或 `claude -p` adapter 运行，统一实现 `VideoAnalyzer` 端口并返回唯一当前态结果契约。分析能力由 `app/analysis_skills/*/SKILL.md` 注册：稳定 Skill ID 不带版本后缀，任务创建时保存完整指令快照，用户可在前端编辑该 Skill 的默认提示词。应用只提供受限 FFmpeg/FFprobe 解码工具，由 AI 自主观察画面并生成连续分镜、逐镜头叙事作用与高光等级、高光、视觉资产和制作建议；不运行 ASR，也不管理模型 API Key。报告以 Markdown 为唯一内容源，可在前端安全预览、下载 `.md`，DOCX 由 `markdown-it-py` 解析同一 Markdown 后生成。当前本机真实视觉 E2E 只通过 Codex；Claude 启用前必须验证实际模型路由具备图片理解。Worker 必须由已经完成 CLI OAuth 登录的本机用户从 `backend/` 启动。

## 运行与就绪

本机必须先提供 PostgreSQL、RabbitMQ、Valkey/Redis 和 MinIO，并预置数据库 schema、消息拓扑、对象存储身份与 bucket。随后从仓库根目录启动业务容器；Compose 不管理这些外部基础设施：

```bash
docker compose --env-file .env -f docker-compose.yml build
docker compose --env-file .env -f docker-compose.yml up -d --force-recreate
docker compose --env-file .env -f docker-compose.yml ps --all
```

宿主机 AI Worker 不属于 Compose。默认启用分析时，从 `backend/` 单独启动且只运行一个实例：

```bash
uv sync --frozen --dev
uv run python -m app.workers.analysis.main
```

API `/health/live` 只证明进程存活；`/health/ready` 还会在有界超时内检查数据库结构、Media Runner、MinIO、RabbitMQ、Valkey，以及启用分析时兼容 AI Worker 的心跳。外部数据库或消息队列重启可能使宿主机 Worker 的长连接中断并退出，应在基础设施恢复后重新启动 Worker，再以 `/health/ready` 返回 `200` 作为交付条件。没有 AI Worker 的部署必须显式设置 `ANALYSIS_ENABLED=false` 并重建 API。

## 测试数据库

后端不安装或兼容 SQLite。Repository 与集成测试默认连接 `postgresql+asyncpg://video:video@127.0.0.1:15432/video`，也可通过 `TEST_DATABASE_URL` 指定另一个 PostgreSQL 数据库。测试账号必须有创建和删除 schema 的权限；每个测试使用独立随机 schema，并在结束时级联清理。

```bash
uv sync --frozen --dev
uv run pytest
```
