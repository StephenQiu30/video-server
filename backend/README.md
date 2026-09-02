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

业务接口要求邮箱账户登录，注册时同时设置唯一用户名。密码使用 Argon2 哈希；短期 Access JWT 与可轮换、可撤销的 Refresh JWT 通过 `HttpOnly` Cookie 维护。JWT 密钥、签发方、受众、Cookie 名、有效期和初始管理员邮箱从根目录 `.env` 的 `AUTH_*` 配置读取，原始 Refresh JWT 不写入数据库。初始管理员邮箱属于保留账号，只有注册请求同时携带与 `AUTH_BOOTSTRAP_ADMIN_SECRET` 匹配的 `X-Admin-Bootstrap-Secret` 请求头时才会创建管理员；普通匿名注册永远只创建普通用户。角色和启用状态以 PostgreSQL 为准，管理员可通过 `/api/admin/users` 管理账号，并通过 `/api/admin/providers` 维护平台状态目录的名称、排序与可见性。平台目录不控制域名匹配、Extractor、Runner 参数或会话能力。

Media Runner 通过 `app/runner/plugins/yt_dlp_plugins/` 加载随项目交付的可信站点提取器。MediaTrack 适配仅处理无需登录的公开审片视频和 API 明确授权的播放转码；抖音适配用数字视频 ID 构造固定公开分享页并修正 landscape 下载规格的短边尺寸语义，TikTok 适配只使用其第一方嵌入播放器 item API 和 yt-dlp 默认客户端，明确无 item/HTTPS 格式、API 临时故障与响应结构漂移分别返回链接不可用、临时不可用和提取器回归，不回退网页挑战；快手适配把公开作品规范化到第一方移动分享页并限制短链重定向域，Tumblr 适配优先读取当前 `www.tumblr.com` 公开页而不强制改写到旧 blog 子域。小红书适配识别第一方 `300031` 笔记失效和 `300012` 平台验证边界，避免把失效内容误报成提取器故障。视频号适配只接受公开 `weixin.qq.com/sph/...` 单视频，并且只在匿名第一方响应直接提供批准腾讯媒体域上的非加密媒体时返回格式；没有公开媒体时明确拒绝并引导用户上传自己拥有或已获授权的文件。所有适配都继续经过受控代理、作品身份校验、大小/时长限制、重新 inspect、FFmpeg 和 ffprobe 校验，不支持图集截断、账号内容、无水印承诺或原文件权限绕过。

主流视频源使用声明式 Provider Profile 接入：`provider_catalog_*.py` 按策略族登记能力和运行参数，`ProviderRegistry.prepare()` 一次解析得到贯穿 inspect/download 的不可变 `ProviderRequest`，`YtDlpCommandBuilder` 只消费该请求生成固定参数，错误由有序 `FailureRule` 归一化。已有 yt-dlp extractor 的公开单视频平台通常只需增加一个 Profile、契约测试和 metadata/media canary；需要自定义解析时再按 yt-dlp 官方插件目录增加可信 extractor，不修改通用命令执行器。未知站点使用无凭据 Generic extractor。可选的 YouTube、抖音、小红书、Reddit、X、Instagram、Facebook、Pinterest 与微信视频号运维会话在操作开始时由宿主 Chrome 按需读取，经一次性认证加密租约交给各自物理隔离的 Docker Runner，并仅在 tmpfs 中建立操作级 `0600` Cookie jar。

macOS 部署可显式安装统一按需助手，在解析进入受控线路时从 Chrome `Default` 读取目标 Provider 的最小域集合；SQL 查询本身按域限制，不先读取所有 Cookie 再过滤。每次 Runner 操作生成一次性 X25519 私钥，助手返回的 Cookie 只能由该操作解密；队列确认后删除密文，Runner 终态删除 tmpfs jar。助手空闲时无进程、不启动 Chrome，也不创建长期 Secret 或专用浏览器 Profile。视频号需要的元宝 localStorage 只复制到随机临时 Profile，计算动态头后销毁。单次读取在独立进程组中执行，15 秒超时、取消或异常都会回收整个进程组。项目仍只通过根 Docker Compose 运行；平台出口信誉需要隔离时，由运维使用 `RUNNER_PROVIDER_EGRESS_PROXIES` 按稳定 key 指向受控内部代理。

完整的 Provider 一次性会话租约、撤销与故障流程见 `docs/operations/003-多平台受控会话运行手册.md`。

视觉分析默认通过宿主机 Codex App Server stdio 协议运行，也支持 `claude -p` adapter 和 Web 管理的 DeepSeek/LangChain 视觉 API，三者统一实现 `VideoAnalyzer` 端口并返回唯一当前态结果契约。每个 Codex 调用创建独立 ephemeral thread，完成后关闭进程，不依赖长期连接。DeepSeek 由 Worker 使用 FFmpeg 均匀生成最多 64 张、总原始证据不超过 24 MiB 的顺序 JPEG，以 base64 内联图片调用视觉模型，不暴露对象地址或客户端文件路径。分析能力由 `app/analysis_skills/*/SKILL.md` 注册；不运行 ASR。第三方 Endpoint、模型与 Key 只通过管理员 Web Profile 配置，Key 使用 Fernet 加密后存入 PostgreSQL 并仅在 Worker 内存中解密，不使用第三方 AI `.env`。报告以 Markdown 为唯一内容源，可安全预览和导出 Markdown/DOCX。Worker 必须在可访问 FFmpeg、队列和对象存储的宿主机运行；默认 Codex 路径还要求同一系统用户已完成官方登录。

内置 `local-codex` 不可删除或改造为第三方结构；模型和线路仅由数据库 Web Profile 决定，`.env` 只保留宿主机 CLI 二进制路径。

## 运行与就绪

本机必须先提供 PostgreSQL、RabbitMQ、Valkey/Redis 和 MinIO，并预置数据库 schema、消息拓扑、对象存储身份与 bucket。随后从仓库根目录启动前端、API 和业务 Worker；Compose 不管理这些外部基础设施：

```bash
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
docker compose --env-file .env -f docker-compose.yml ps --all
```

这是完整项目唯一的运行入口。更新代码时先独立执行 `git pull --ff-only`，再重复
该 Compose 命令；不要使用不会应用代码、镜像或配置变化的
`docker compose restart`。固定 Provider 探针是独立验收步骤，不参与服务启动。

本地开发复用 Homebrew 的 PostgreSQL、RabbitMQ、Redis 和 MinIO，业务进程仍只通过根 Compose 启动。根目录 `.env` 应分别使用标准端口 `5432`、`5672`、`6379` 和 `9000`。确认 `brew services list` 中四项均为 `started` 后，从根目录执行：

```bash
docker compose --env-file .env -f docker-compose.yml \
  up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
```

该入口启动前端、API、Media Runner、Outbox、下载/导入/报告 Worker、Provider Canary 和已声明的 Operator Profile；所有进程读取根目录 `.env`。只启动 API 时，HTTP 查询仍可用，但 Outbox 不会发布、异步任务不会被消费，平台状态也无法取得 Runner 上下文。

只调试无异步依赖的 API 路由时，才使用 Python 模块入口：

```bash
uv sync --frozen --dev
uv run python -m app.main
```

该命令是后端模块调试入口，不替代完整本地拓扑中的 Worker、Runner 与前端构建。

当 `.env` 的 `RUNNER_OPERATOR_BASE_URLS` 声明 Provider Operator 时，需要使用受控
会话的平台还必须启动对应 Profile：

```bash
docker compose --env-file .env -f docker-compose.yml \
  --profile youtube-operator \
  --profile douyin-operator --profile xiaohongshu-operator \
  --profile reddit-operator --profile x-operator \
  --profile instagram-operator --profile facebook-operator \
  --profile pinterest-operator --profile wechat-channels-operator up -d --build
```

API readiness 会检查所有已配置的 Operator endpoint。生产 Compose 固定启动九个隔离
Runner，并在 API、下载 Worker 与 Canary 启动前等待其健康；不能在受控路径缺失时错误
报告就绪。开发环境只需启用 `.env` 实际声明的平台 Profile。

固定 Provider 诊断矩阵和真实媒体探针命令见
`docs/operations/007-固定Provider探针运行手册.md`。

`GET /api/providers` 将 Registry 发布验收基线、近期固定探针和已经生成完整制品的
真实下载合并展示。长期无人使用或未配置探针不会撤销已验收能力；近期重复失败仍会
自动降级对应平台。真实任务投影只使用非敏感 Provider 上下文与完成时间，不读取或
公开来源 URL、账号和 Cookie。`browser` 只是本机动态来源标识；关联的近期成功
表示该来源曾在相同非敏感上下文生成完整制品，不是当前 Cookie 内容 cohort，也不能单独证明
当前会话可用或将 `access_required` 提升为 `verified`。

宿主机 AI Worker 不属于 Compose，默认作为本机 Codex App Server Worker 独立受监督；第三方 Provider 从 Web 管理页选择，不通过额外启动脚本或 `.env` 切换。只使用跨平台 Agent 管理入口：

```bash
uv sync --frozen --dev
uv run python -m app.workers.analysis.agent_cli doctor
uv run python -m app.workers.analysis.agent_cli install
uv run python -m app.workers.analysis.agent_cli status
```

上述命令默认读取仓库根目录 `.env`。当业务容器通过 `.env.prod` 运行时，宿主机
Agent 必须显式使用同一环境文件，避免 API、队列和对象存储落到不同环境：

```bash
uv run python -m app.workers.analysis.agent_cli doctor --env-file ../.env.prod
uv run python -m app.workers.analysis.agent_cli install --env-file ../.env.prod
```

API 固定监听 `8111`，前端固定监听 `8101`。API `/health/live` 只证明进程存活；`/health/ready` 还会在有界超时内检查数据库结构、Media Runner、MinIO、RabbitMQ 与 Valkey。宿主机 AI Worker 内部重连消费者并由系统服务监督进程；短暂故障期间任务保持 queued，恢复后继续消费。没有 AI Worker 的部署必须显式设置 `ANALYSIS_ENABLED=false` 并重建 API。

## 测试数据库

后端不安装或兼容 SQLite。Repository 与集成测试默认读取根 `.env` 的 `DATABASE_URL` 并连接宿主机现有的 PostgreSQL `5432`，不会为测试启动 Docker PostgreSQL；`TEST_DATABASE_URL` 可显式覆盖。没有根 `.env` 时才使用 `postgresql+asyncpg://video:video@127.0.0.1:5432/video`。测试账号必须有创建和删除 schema 的权限；每个测试使用独立随机 schema，并在结束时级联清理。

```bash
uv sync --frozen --dev
uv run pytest
```
