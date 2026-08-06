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

入口为 <http://localhost:19090>。默认环境的稳定非敏感配置直接写在 Compose 中，不要求 `.env`；只有真实 AI 调用需要注入 `OPENAI_API_KEY`。PostgreSQL 在全新数据卷首次启动时以单事务执行 `backend/sql/schema.sql`，健康检查同时验证关键业务表；代码进程只在依赖健康后启动。项目不提供旧数据卷升级兼容，schema 变化后应使用新数据卷验证。

统一镜像在 builder 与 runtime 中都使用 `/app/backend`，虚拟环境固定为 `/app/backend/.venv`。不要把 builder 改回其他绝对目录后直接复制 venv；API、Worker 与 Runner 均通过该 venv 的 `python -m ...` 入口启动。

## 仅依赖环境

```bash
docker compose -f docker-compose-env.yml up -d
```

此模式不会启动 API、Worker、Runner 或前端构建。为避开常见本机服务，宿主机使用固定项目端口：PostgreSQL `localhost:15432`、RabbitMQ `localhost:5673`（管理台 `15673`）、MinIO `localhost:19000`（控制台 `19001`）。这些地址也是后端类型化配置的本地默认值。

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

- PostgreSQL、RabbitMQ、MinIO 使用 Compose 项目作用域卷；完整环境与仅依赖环境分别属于 `server` 和 `server-env`，不会争用同一数据卷。
- Runner 与下载 Worker 共享的工作卷只保存单任务临时文件；成功上传或失败后均应清理。
- 常规停止使用 `docker compose down`，不得在未确认备份时添加 `--volumes`。
- `.env`、用户 URL、Cookie、Authorization、provider key 和完整模型输出不得进入日志或提交。

## 最小检查

```bash
curl --fail http://localhost:19090/health/live
curl --fail http://localhost:19090/health/ready
docker compose -f docker-compose.yml ps
```

若下载解析失败，先区分 URL/格式业务错误、Runner 健康、egress ACL、队列积压和对象存储，不要通过开放私网、上传 Cookie 或透传 yt-dlp 参数绕过控制。
