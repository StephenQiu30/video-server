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

Media Runner 通过 `app/runner/plugins/yt_dlp_plugins/` 加载随项目交付的可信站点提取器。当前 MediaTrack 适配仅处理无需登录的公开审片视频和 API 明确授权的播放转码；不支持 Cookie、账号内容或原文件下载权限绕过。

文本分析统一通过 LangChain 的结构化输出接口运行，服务端以 `ANALYSIS_PROVIDER=ollama|deepseek` 选择本地 Ollama 或 DeepSeek。Ollama 默认模型为 `deepseek-r1:8b`，DeepSeek 默认模型为 `deepseek-v4-flash`。音频转录是独立 ASR 端口，不与文本模型配置混用。
