# Backend

FastAPI API、下载/分析领域逻辑、异步 Worker、当前态数据库 SQL 和 Python 测试位于本模块。

所有 Python 与 `uv` 命令都应从 `backend/` 执行。数据库当前结构定义在 `sql/schema.sql`，由 PostgreSQL 在全新数据卷中初始化；项目不维护迁移或旧 schema 兼容路径。生产镜像由仓库根目录 `Dockerfile` 统一构建。

## 目录约定

```text
app/
├── api/              FastAPI 装配、健康检查与 HTTP 契约
│   ├── routes/       `/api/*` 路由
│   └── schemas/      请求与响应模型
├── application/      用例编排与外部能力端口
├── domain/           不依赖框架的领域规则
├── infrastructure/   数据库、消息、对象存储和模型适配器
├── runner/           无业务凭据的媒体执行进程
├── workers/          Outbox、下载和分析进程入口
├── composition.py    运行时依赖装配
└── main.py           FastAPI 进程入口
```

依赖方向保持为 `api/workers → application → domain`。FastAPI DTO 位于 `api/schemas/`；不要把数据库模型、Provider SDK 或 Worker 实现移入 `domain`。

公共接口不维护无实际兼容需求的版本目录或 URL 前缀。服务启动后可通过 `/docs` 访问 Swagger UI，通过 `/openapi.json` 获取供前端生成客户端的 OpenAPI 契约。

业务接口要求邮箱账户登录。密码使用 Argon2 哈希；短期 Access JWT 与可轮换、可撤销的 Refresh JWT 通过 `HttpOnly` Cookie 维护。JWT 密钥、签发方、受众、Cookie 名和有效期从根目录 `.env` 的 `AUTH_*` 配置读取，原始 Refresh JWT 不写入数据库。

Media Runner 通过 `app/runner/plugins/yt_dlp_plugins/` 加载随项目交付的可信站点提取器。当前 MediaTrack 适配仅处理无需登录的公开审片视频和 API 明确授权的播放转码；不支持 Cookie、账号内容或原文件下载权限绕过。

主流视频源通过 `app/runner/provider_registry.py` 与 `app/runner/provider_catalog.py` 采用 Strategy + Registry 统一匹配；`provider_urls.py` 只保留兼容入口，未知站点使用 yt-dlp Generic extractor。新增平台应先确认 yt-dlp extractor 存在，再补充 Profile、域名别名和解析测试。Runner 不再为命令创建或传入空 Cookie 文件；平台出口信誉需要隔离时，由运维使用 `RUNNER_PROVIDER_EGRESS_PROXIES` 按稳定 Provider key 指向受控内部代理。

文本分析统一通过 LangChain 的结构化输出接口运行，服务端以 `ANALYSIS_PROVIDER=ollama|deepseek` 选择本地 Ollama 或 DeepSeek。Ollama 默认模型为 `qwen3:latest`，DeepSeek 默认模型为 `deepseek-v4-flash`。音频转录是独立 ASR 端口，不与文本模型配置混用。
