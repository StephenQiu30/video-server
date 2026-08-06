# 根目录 Compose 运行手册

## 三个固定入口

| 文件 | 独立使用 | 职责 |
| --- | --- | --- |
| `docker-compose.yml` | 是 | 默认完整系统：API/同源前端、Outbox、下载与 AI Worker、Media Runner、egress proxy、PostgreSQL、RabbitMQ、MinIO |
| `docker-compose-env.yml` | 是 | 仅启动 PostgreSQL、RabbitMQ、MinIO 及 MinIO 初始化器，供宿主机开发 |
| `docker-compose-prod.yml` | 否 | 生产覆盖；必须叠加默认文件，禁用本地 build 并强制镜像和密钥 |

仓库不使用 `deploy/` 目录，也不运行独立生产前端容器。

## 默认完整启动

```bash
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up --build
```

入口为 <http://localhost:19090>。默认文本模型配置指向宿主机已有的 Ollama 服务与 `deepseek-r1:8b`，项目不会安装 Ollama 或拉取模型；运行环境应确保容器可访问 `host.docker.internal:11434`。切换云端 DeepSeek 时设置 `ANALYSIS_PROVIDER=deepseek` 和 `DEEPSEEK_API_KEY`。真实视频分析还需要独立的 `OPENAI_API_KEY` 执行音频转录。PostgreSQL 在全新数据卷首次启动时以单事务执行 `backend/sql/schema.sql`，健康检查同时验证关键业务表；代码进程只在依赖健康后启动。项目不提供旧数据卷升级兼容，schema 变化后应使用新数据卷验证。

默认完整栈名为 `video-server`，容器使用 `video-server-api`、`video-server-postgres` 等稳定名称，不附加 Compose 副本序号。API 绑定 `127.0.0.1:19090`；MinIO API 与控制台绑定 `127.0.0.1:19000/19001`，避免和本机常见的 `9000/9001` 冲突。多实例或端口冲突场景可在启动命令环境中显式提供 `COMPOSE_CONTAINER_PREFIX`、`COMPOSE_BIND_ADDRESS`、`COMPOSE_API_PORT`、`COMPOSE_MINIO_API_PORT` 和 `COMPOSE_MINIO_CONSOLE_PORT`，普通本地开发不需要把这些默认值写入 `.env`。

统一镜像在 builder 与 runtime 中都使用 `/app/backend`，虚拟环境固定为 `/app/backend/.venv`。不要把 builder 改回其他绝对目录后直接复制 venv；API、Worker 与 Runner 均通过该 venv 的 `python -m ...` 入口启动。

## 仅依赖环境

```bash
docker compose -f docker-compose-env.yml up -d
```

此模式不会启动 API、Worker、Runner 或前端构建。为避开常见本机服务，宿主机使用固定项目端口：PostgreSQL `localhost:15432`、RabbitMQ `localhost:5673`（管理台 `15673`）、MinIO `localhost:19000`（控制台 `19001`）。这些地址也是后端类型化配置的本地默认值。

仅依赖栈名为 `video-server-env`，容器名为 `video-server-dev-postgres`、`video-server-dev-rabbitmq`、`video-server-dev-minio` 和一次性 `video-server-dev-minio-init`。如本机已运行这些依赖，不需要启动该栈；在被 Git 忽略的根 `.env` 中只设置与类型化默认值不同的 `DATABASE_URL`、`RABBITMQ_URL`、`MINIO_ENDPOINT` 和对应凭据。Compose 隔离环境有自己的 YAML 默认值，宿主机连接变量不会覆盖容器内部 DNS。

## 生产覆盖

```bash
cp .env.prod.example .env.prod
# 替换全部 replace-with-*；数据库/MQ 密码使用 URL-safe 字符，并生成有效 Fernet key
docker compose --env-file .env.prod \
  -f docker-compose.yml -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod \
  -f docker-compose.yml -f docker-compose-prod.yml up -d
```

生产配置使用严格 `blocked-destinations.conf`。Docker Desktop 开发环境使用专用 ACL 处理其 `198.18/15` 合成 DNS，但仍拒绝字面量 IP URL 和其他非公网范围；Linux 开发环境直接使用严格 ACL。

## 网络边界

- `app_ingress`：只连接 API 与 MinIO，承载页面/API 入口以及浏览器使用的短时签名文件地址。
- `core`：internal 网络，连接 PostgreSQL、RabbitMQ、MinIO 与需要它们的代码进程。
- `runner_control`：internal 网络，仅用于 API/下载 Worker 调用 Media Runner 及 Runner 访问 egress proxy。
- `public_egress` 只授予 egress proxy；`ai_egress` 只授予 AI Worker。DB、MQ 和下载 Worker 不直接获得公网出口。

## 数据和临时文件

- PostgreSQL、RabbitMQ、MinIO 使用 Compose 项目作用域卷；完整环境与仅依赖环境分别属于 `video-server` 和 `video-server-env`，不会争用同一数据卷。
- Runner 与下载 Worker 共享的工作卷只保存单任务临时文件；成功上传或失败后均应清理。
- 所有长运行服务使用大小和数量受限的 `json-file` 日志轮转，默认每文件 `10m`、保留 `3` 个；特殊部署可在启动命令环境中覆盖。
- 常规停止使用 `docker compose down`，不得在未确认备份时添加 `--volumes`。
- `.env`、用户 URL、Cookie、Authorization、provider key 和完整模型输出不得进入日志或提交。

## 最小检查

```bash
curl --fail http://localhost:19090/health/live
curl --fail http://localhost:19090/health/ready
docker compose -f docker-compose.yml ps
```

若下载解析失败，先区分 URL/格式业务错误、Runner 健康、egress ACL、队列积压和对象存储，不要通过开放私网、上传 Cookie 或透传 yt-dlp 参数绕过控制。
