# 根目录 Compose 运行手册

## 两个固定职责

| 文件 | 职责 |
| --- | --- |
| `docker-compose.yml` | 完整服务拓扑；基础设施与初始化任务位于 `environment` Profile |
| `docker-compose-prod.yml` | 生产 `.env.prod`、生产镜像和对外端口 |

仓库不维护额外的环境 Compose 文件。运行服务、可选基础设施和各自的初始化命令都在同一服务文件中；本机已有基础设施时不启用 `environment` Profile，需要完整隔离环境时才启用。需要复用本机 OAuth 的 AI Worker 明确排除在 Compose 外。生产文件只覆盖生产差异，不复制整套服务。

## 本地环境

```bash
cp .env.example .env
docker compose --env-file .env -f docker-compose.yml config --quiet
docker compose --env-file .env \
  -f docker-compose.yml --profile environment \
  config --quiet
docker compose --env-file .env \
  -f docker-compose.yml --profile environment \
  up -d database-init rabbitmq-init valkey minio-init
docker wait database-init rabbitmq-init minio-init
docker compose --env-file .env -f docker-compose.yml up -d --build
```

第一条 `up` 只启动可选基础设施并等待三个初始化任务成功；`database-init` 会幂等执行 `backend/sql/schema.sql`。随后再启动运行服务，避免把数据库初始化隐藏在环境变量或镜像入口中。可用 `docker compose --env-file .env -f docker-compose.yml logs database-init` 检查结果。

入口为 <http://localhost:8101>。Swagger UI 位于 <http://localhost:8101/docs>，OpenAPI 契约位于 <http://localhost:8101/openapi.json>。已有本机基础设施时跳过第一条 `up`，并在 `.env` 中把连接地址设置为容器可达地址；本机进程使用回环地址，Docker Desktop 容器通常使用 `host.docker.internal`。

如果 API、Worker 和 Runner 都在本机运行，只需要 Docker 提供受控出口代理：

```bash
docker compose --env-file .env \
  -f docker-compose.yml \
  up -d egress-proxy
```

该命令只启动 `egress-proxy`，不会启动 PostgreSQL、RabbitMQ、Valkey 或 MinIO。将本机 Runner 的 `RUNNER_EGRESS_PROXY` 指向 `http://127.0.0.1:${EGRESS_PROXY_HOST_PORT:-13128}`。

AI 分析还需由已登录 Codex 或 Claude CLI 的同一宿主机用户启动：

```bash
cd backend
uv run python -m app.workers.analysis.main
```

Worker preflight 通过后才连接 RabbitMQ；不要同时启动另一个分析消费者。本地 API 默认开启 `ANALYSIS_ENABLED`。

`SCREENPLAY_ANALYSIS_ENABLED` 独立控制剧本分析/改写任务，当前默认关闭。受限执行链只支持 Claude CLI：`screenplay-analysis` 默认单次最多 120,000 字符和 120 个源场景；`screenplay-rewrite` 默认先对最多 120,000 字符生成 glossary，再按 8,000 字符分为最多 128 块，每块携带前后各 1,000 字符上下文，全部改写正文合计最多 400,000 字符。当前块遇到可恢复失败时默认在同一 run/attempt 内最多调用 2 次、首次等待 1 秒，已验证块不会重复调用，新的 attempt 不复用旧输出。对应配置为 `ANALYSIS_SCREENPLAY_SINGLE_CALL_CHARACTERS`、`ANALYSIS_SCREENPLAY_REWRITE_CHUNK_CHARACTERS`、`ANALYSIS_MAX_SCREENPLAY_REWRITE_CHUNKS`、`ANALYSIS_SCREENPLAY_REWRITE_CONTEXT_CHARACTERS`、`ANALYSIS_MAX_SCREENPLAY_REWRITE_OUTPUT_CHARACTERS`、`ANALYSIS_SCREENPLAY_REWRITE_CHUNK_CALL_ATTEMPTS` 和 `ANALYSIS_SCREENPLAY_REWRITE_CHUNK_RETRY_DELAY_SECONDS`。开启后 Worker 会在连接 RabbitMQ 前同时预检分析和改写能力；Codex 或任一能力缺失会 fail closed。只有中文/英文真实 Provider E2E、报告和浏览器流程通过后才可在正式环境设为 `true`；单独开启 `ANALYSIS_ENABLED` 只代表视频分析可创建。

所有服务都显式声明 `container_name`；公开主服务使用 `video-server`，基础服务使用 `postgres`、`rabbitmq`、`minio` 等简单名称，不会出现 `xxx-1` 副本后缀。环境配置读取被 Git 忽略的 `.env`，首次启动前从 `.env.example` 复制。

## 生产环境

```bash
cp .env.prod.example .env.prod
# 替换 .env.prod 中全部 replace-with-* 占位值
docker compose --env-file .env.prod \
  -f docker-compose.yml -f docker-compose-prod.yml --profile environment \
  config --quiet
docker compose --env-file .env.prod \
  -f docker-compose.yml -f docker-compose-prod.yml --profile environment \
  up -d database-init rabbitmq-init valkey minio-init
docker wait database-init rabbitmq-init minio-init
docker compose --env-file .env.prod \
  -f docker-compose.yml -f docker-compose-prod.yml \
  up -d --build
```

生产文件只提供生产环境差异，并在 Compose 解析阶段检查关键配置是否存在；生产运行前必须替换 `.env.prod` 中的占位值。生产 API 默认开启分析入口，Compose 只把 PostgreSQL、RabbitMQ 和 MinIO 的必要端口发布到宿主机 loopback，不运行 AI Worker。使用同一份生产配置另开宿主机进程：

```bash
cd backend
uv run --env-file ../.env.prod python -m app.workers.analysis.main
```

Worker preflight 成功并持续运行后才能接收分析任务；若没有宿主机 Worker，应显式设置 `ANALYSIS_ENABLED=false` 后重建 API，避免继续创建无人消费的任务。

## 网络边界

- PostgreSQL、RabbitMQ、Valkey、MinIO、Runner RPC 和 Runner 出口分别使用独立网络；数据库、队列、配额、存储和 Runner RPC 网络均为 `internal`。为宿主机 AI Worker 仅把 PostgreSQL、RabbitMQ 和 MinIO 的必要端口绑定到 `127.0.0.1`，不向公网发布。
- API 与 Worker 只加入它们实际需要的内部网络；为允许容器复用宿主机已有环境，它们同时通过普通应用网络访问 `.env` 指定的连接地址。宿主机 AI Worker 通过独立的 `ANALYSIS_*` 地址访问基础设施；Outbox 不加入存储或 Runner 网络。
- 默认 `media-runner` 只收到 Runner 运行时变量（HMAC、工作目录和受控代理），不获得 Provider Secret。显式启用 `youtube-operator` Profile 时，独立 `youtube-operator-runner` 只能读取版本化 YouTube Cookie Secret，并在 Runner 独占 tmpfs 生成操作级副本；它仍不能获得数据库、队列、对象存储、Valkey 或 AI 凭据。
- Compose 内的 Runner、下载 Worker 与 Canary 统一把共享命名卷挂载到固定的 `/work`，该容器路径不读取宿主机 `RUNNER_WORKSPACE_ROOT` 覆盖；宿主机直接运行 Runner 时才按本机环境单独设置工作目录，避免两侧返回不可访问的制品路径。
- Media Runner 通过 egress proxy 访问外部媒体地址；本地环境组合只把代理绑定到宿主机回环地址，供本机 Runner 复用，并继续拒绝私网、localhost 和字面量 IP 目的地址。生产覆盖移除该端口。
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
docker compose --env-file .env \
  -f docker-compose.yml \
  ps
```

若下载解析失败，先区分 URL/格式、会话、请求证明、出口信誉、egress ACL、Runner、队列和对象存储。不要在普通解析请求中粘贴 Cookie、开放私网或透传 yt-dlp 参数；受控 Provider 会话的导入、轮换和撤销只按 005 及专用运维 runbook 执行。

YouTube 运维会话默认关闭。只有完成账号最小权益检查、Cookie 域验证和授权样本 canary 后，才按 [YouTube 受控会话运行手册](002-YouTube受控会话运行手册.md)启用 `youtube-operator` Profile；缺少任一门禁时保持匿名拓扑。
