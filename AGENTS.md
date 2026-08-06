# Server 项目规范

## 仓库与运行方式

- 仓库只保留 `backend/`、`frontend/`、`docs/` 三个业务模块以及一套根治理文件，不创建 `deploy/` 或重复子仓库。
- 根 `Dockerfile` 构建前后端统一镜像；根 `docker-compose.yml` 启动完整本地系统，`docker-compose-env.yml` 只启动开发依赖，`docker-compose-prod.yml` 是生产覆盖文件。
- 开发 Compose 必须零配置可启动；镜像版本、内部服务名、队列、端口、网络、卷和限制使用版本化固定值或类型化代码默认值。外部 env 只用于生产镜像、凭据、密钥和公共端点。
- PostgreSQL 只通过 `backend/sql/schema.sql` 初始化全新数据库。项目不保留迁移目录、历史 schema 或旧版本兼容逻辑；结构变化时直接更新当前态 SQL 与 ORM，并使用新数据卷验证。
- 产品与技术事实以 `docs/` 的当前文档为准；删除内容通过 Git 历史追溯，不复制为新基线。

## 架构边界

- 后端依赖方向为 `api/workers → application → domain`。领域层不得导入 FastAPI、SQLAlchemy、RabbitMQ、MinIO、yt-dlp、FFmpeg 或模型 SDK。
- API、下载 Worker、媒体 Runner、AI Worker是独立进程；HTTP 请求内不得执行下载、转码、ASR 或 LLM 长任务。
- PostgreSQL 是状态事实来源；跨 PostgreSQL/RabbitMQ 使用 transactional outbox，消费者必须支持幂等与 lease/heartbeat。
- 前端遵循 Ant Design Pro / Umi Max 约定，以 `pages/`、`components/`、`services/`、`hooks/` 和 `utils/` 分工；只访问同源 `/api/*`、`/health/*` 和短时制品地址。生产静态资源由 FastAPI 提供，不设置独立前端容器。
- OpenAPI 是前后端契约来源，不维护平行 DTO 或旧 API 适配层。

## 下载、AI 与安全

- 仅处理用户有权下载和分析的公开、非 DRM HTTP(S) 内容；禁止 Cookie 上传、DRM 绕过、私网 URL、任意 yt-dlp 参数与 shell 输入。
- 媒体流量只能由无业务凭据的 Runner 发起并经过阻断私网的 egress proxy；入口 URL 校验不能替代网络隔离。
- Worker 开工前重新解析语义下载计划；provider format id 不能作为唯一恢复依据。
- AI 任务独立于下载任务；AI 失败不得改变下载成功状态。模型输出必须通过 schema 和 transcript evidence 校验，普通日志不得记录完整转录或原始模型响应。
- Secret 仅来自类型化配置与环境变量，不得进入前端、API 响应、异常、快照或普通日志。所有外部操作必须设置大小、时长、并发与超时上限，取消时终止整个子进程组。

## 实现与验证

- 只实现当前需求，不添加旧结构、旧 API、旧 Provider 或旧数据库的兼容分支。
- 测试聚焦领域规则、API 契约、安全边界和关键成功/失败流程；不为覆盖率数字复制测试或断言实现细节。
- Mock 测试不能替代 PostgreSQL、RabbitMQ、MinIO、yt-dlp/FFmpeg 与模型 Provider 的受控集成验证。
- 后端提交前运行 Ruff、format、strict mypy、pytest；前端运行 lint、format、typecheck、tests、build；运行时变更还要校验三个 Compose 配置和统一镜像构建。
- 单文件目标不超过 200 行；超过时按职责拆分。
- 交付资料按 `Design → PRD → Plan → Acceptance` 维护，并让验收状态与真实证据一致。
