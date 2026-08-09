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

本地配置可直接启动 API、下载链路与基础设施。入口为 <http://localhost:8101>。Swagger UI 位于 <http://localhost:8101/docs>，OpenAPI 契约位于 <http://localhost:8101/openapi.json>。

AI 分析还需由已登录 Codex 或 Claude CLI 的同一宿主机用户启动：

```bash
cd backend
uv run python -m app.workers.analysis.main
```

Worker preflight 通过后才连接 RabbitMQ；不要同时启动另一个分析消费者。当前生产 Compose 使用 `ANALYSIS_ENABLED=false`，不会创建无人消费的分析任务。

所有服务都显式声明 `container_name`；公开主服务使用 `video-server`，基础服务使用 `postgres`、`rabbitmq`、`minio` 等简单名称，不会出现 `xxx-1` 副本后缀。环境配置读取被 Git 忽略的 `.env`，首次启动前从 `.env.example` 复制。

## 生产环境

```bash
cp .env.prod.example .env.prod
# 替换 .env.prod 中全部 replace-with-* 占位值
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml up -d --build
```

生产文件只提供生产环境差异，并在 Compose 解析阶段检查关键配置是否存在；生产运行前必须替换 `.env.prod` 中的占位值。

## 网络边界

- PostgreSQL、RabbitMQ、Valkey、MinIO、Runner RPC 和 Runner 出口分别使用独立网络；数据库、队列、配额、存储和 Runner RPC 网络均为 `internal`，不允许从宿主机或公网直接进入。
- API、下载 Worker 只加入它们实际需要的内部网络；宿主机 AI Worker 通过 `.env` 中独立的 `ANALYSIS_*` 地址访问发布到 loopback 的基础设施；Outbox 不加入存储或 Runner 网络。
- 当前 Media Runner 只收到 Runner 运行时变量（HMAC、工作目录和受控代理），业务数据库、队列、对象存储、会话密钥和 Provider Key 不注入 Runner。005 的 credentialed Runner 尚未实现；未来也只能使用单 Provider 只读 Secret/短租约，不能获得业务 Secret。
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
