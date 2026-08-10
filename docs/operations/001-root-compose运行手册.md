# 根目录 Compose 运行手册

## 两个固定职责

| 文件 | 职责 |
| --- | --- |
| `docker-compose.yml` | 本地 `.env`、API/下载拓扑、基础设施、健康检查和卷 |
| `docker-compose-prod.yml` | 生产 `.env.prod`、生产镜像和对外端口 |

本地文件集中定义容器服务拓扑和本地环境配置；需要复用本机 OAuth 的 AI Worker 明确排除在 Compose 外。生产文件只覆盖生产差异，不复制整套服务。仓库不使用 `deploy/` 目录。环境变量的具体值只写在 `.env.example`、`.env.prod.example` 或被 Git 忽略的 `.env*` 文件中。

## 本地环境

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.yml config --quiet
docker compose --env-file .env -f docker-compose.yml up -d --build
```

Compose 会先等待 PostgreSQL 健康，再由一次性 `database-init` 容器幂等执行
`backend/sql/schema.sql`。API、Outbox 和下载 Worker 只有在数据库初始化成功后才启动；
因此全新卷和缺少当前表/索引的已有卷都不需要手工执行 SQL。可用
`docker compose --env-file .env -f docker-compose.yml logs database-init` 检查初始化结果。

本地配置可直接启动 API、下载链路与基础设施。入口为 <http://localhost:8101>。Swagger UI 位于 <http://localhost:8101/docs>，OpenAPI 契约位于 <http://localhost:8101/openapi.json>。

AI 分析还需由已登录 Codex 或 Claude CLI 的同一宿主机用户启动：

```bash
cd backend
uv run python -m app.workers.analysis.main
```

Worker preflight 通过后才连接 RabbitMQ；不要同时启动另一个分析消费者。本地 API 默认开启 `ANALYSIS_ENABLED`。

所有服务都显式声明 `container_name`；公开主服务使用 `video-server`，基础服务使用 `postgres`、`rabbitmq`、`minio` 等简单名称，不会出现 `xxx-1` 副本后缀。环境配置读取被 Git 忽略的 `.env`，首次启动前从 `.env.example` 复制。

## 生产环境

```bash
cp .env.prod.example .env.prod
# 替换 .env.prod 中全部 replace-with-* 占位值
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml up -d --build
```

生产文件只提供生产环境差异，并在 Compose 解析阶段检查关键配置是否存在；生产运行前必须替换 `.env.prod` 中的占位值。生产 API 默认开启分析入口，Compose 只把 PostgreSQL、RabbitMQ 和 MinIO 的必要端口发布到宿主机 loopback，不运行 AI Worker。使用同一份生产配置另开宿主机进程：

```bash
cd backend
uv run --env-file ../.env.prod python -m app.workers.analysis.main
```

Worker preflight 成功并持续运行后才能接收分析任务；若没有宿主机 Worker，应显式设置 `ANALYSIS_ENABLED=false` 后重建 API，避免继续创建无人消费的任务。

## 网络边界

- PostgreSQL、RabbitMQ、Valkey、MinIO、Runner RPC 和 Runner 出口分别使用独立网络；数据库、队列、配额、存储和 Runner RPC 网络均为 `internal`。为宿主机 AI Worker 仅把 PostgreSQL、RabbitMQ 和 MinIO 的必要端口绑定到 `127.0.0.1`，不向公网发布。
- API、下载 Worker 只加入它们实际需要的内部网络；宿主机 AI Worker 通过 `.env` 中独立的 `ANALYSIS_*` 地址访问发布到 loopback 的基础设施；Outbox 不加入存储或 Runner 网络。
- 默认 `media-runner` 只收到 Runner 运行时变量（HMAC、工作目录和受控代理），不获得 Provider Secret。显式启用 `youtube-operator` Profile 时，独立 `youtube-operator-runner` 只能读取版本化 YouTube Cookie Secret，并在 Runner 独占 tmpfs 生成操作级副本；它仍不能获得数据库、队列、对象存储、Valkey 或 AI 凭据。
- Media Runner 通过 egress proxy 访问外部媒体地址；proxy 不暴露宿主机端口，并继续拒绝私网、localhost 和字面量 IP 目的地址。
- 容器内 API、下载 Worker 与 Runner 使用 Compose DNS 互联；只有宿主机 AI Worker 使用 loopback 发布端口。

当某个平台因数据中心出口信誉触发访问验证时，可以让运维侧提供一个同样受控、无凭据的内部代理入口，并按 Provider 覆盖默认出口：

```dotenv
RUNNER_PROVIDER_EGRESS_PROXIES={"youtube":"http://youtube-egress:3128","douyin":"http://douyin-egress:3128"}
```

键使用 Provider Registry 中的稳定 key；未配置的平台继续使用 `RUNNER_EGRESS_PROXY`。覆盖地址本身不得携带用户名或密码，内部代理仍须阻断私网目的地址、限制目标端口并在代理侧管理上游凭据。默认值 `{}` 不改变现有拓扑。该能力用于出口隔离和信誉治理，不能用于绕过 DRM、账号权限或平台访问控制。

## 数据和停止

- 本地和生产组合统一使用 Compose 项目名 `video-server` 及其作用域卷；两套环境容器名和数据卷相同，同一主机不要同时启动。
- Runner 与下载 Worker 共享的工作卷只保存单任务临时文件；成功上传或失败后均应清理。
- 常规停止使用与启动相同的文件组合执行 `docker compose ... down`；不得在未确认备份时添加 `--volumes`。
- `.env`、用户 URL、Cookie、Authorization、provider key 和完整模型输出不得进入日志或提交。

## 最小检查

```bash
curl --fail http://localhost:8101/health/live
curl --fail http://localhost:8101/health/ready
docker compose --env-file .env -f docker-compose.yml ps
```

若下载解析失败，先区分 URL/格式、会话、请求证明、出口信誉、egress ACL、Runner、队列和对象存储。不要在普通解析请求中粘贴 Cookie、开放私网或透传 yt-dlp 参数；受控 Provider 会话的导入、轮换和撤销只按 005 及专用运维 runbook 执行。

YouTube 运维会话默认关闭。只有完成账号最小权益检查、Cookie 域验证和授权样本 canary 后，才按 [YouTube 受控会话运行手册](002-YouTube受控会话运行手册.md)启用 `youtube-operator` Profile；缺少任一门禁时保持匿名拓扑。
