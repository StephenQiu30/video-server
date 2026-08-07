# 根目录 Compose 运行手册

## 三个固定入口

| 文件 | 职责 |
| --- | --- |
| `docker-compose.yml` | 本地应用：API/同源前端、Outbox、下载与 AI Worker、Media Runner、egress proxy |
| `docker-compose-env.yml` | 本地基础设施：PostgreSQL、RabbitMQ、MinIO 及 MinIO 初始化器 |
| `docker-compose-prod.yml` | 生产应用：API/同源前端、Outbox、下载与 AI Worker、Media Runner、egress proxy |

三份文件互不叠加，也不引用另一个文件中的 service、volume 或 network；每份文件都可以单独执行。仓库不使用 `deploy/` 目录。Compose 文件只声明服务编排、容器名、端口、卷和 env 文件引用；环境变量的具体值只写在 `.env.example`、`.env.prod.example` 或被 Git 忽略的 `.env*` 文件中。

## 完整启动

```bash
cp .env.example .env
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up -d --build
```

本地应用栈本身不启动数据库、消息队列或对象存储；首次运行应先启动环境栈。入口为 <http://localhost:8101>。Swagger UI 位于 <http://localhost:8101/docs>，OpenAPI 契约位于 <http://localhost:8101/openapi.json>。

所有服务都显式声明 `container_name`，容器名稳定为 `video-server-local-api`、`video-server-env-postgres` 等，不会出现 `xxx-1` 副本后缀。默认本地应用读取被 Git 忽略的 `.env`，首次启动前从 `.env.example` 复制。

## 本地基础设施

```bash
cp .env.example .env
docker compose -f docker-compose-env.yml config --quiet
docker compose -f docker-compose-env.yml up -d
```

此模式不会启动 API、Worker、Runner 或前端构建。固定宿主机端口为：PostgreSQL `localhost:15432`、RabbitMQ `localhost:5673`（管理台 `15673`）、MinIO `localhost:19190`（控制台 `19191`）。本地应用容器通过 `.env` 中的 `host.docker.internal` 访问这些端口。

## 生产应用

```bash
cp .env.prod.example .env.prod
# 替换 .env.prod 中全部 replace-with-* 占位值
docker compose -f docker-compose-prod.yml config --quiet
docker compose -f docker-compose-prod.yml up -d --build
```

生产文件是完整独立的应用入口，不依赖本地 Compose 文件。生产运行前必须替换 `.env.prod` 中的占位值，并确保其中的数据库、消息队列和对象存储地址可从生产容器访问。

## 网络边界

- 服务使用 Compose 默认网络互联，不额外维护命名网络。
- Media Runner 通过 egress proxy 访问外部媒体地址；proxy 不暴露宿主机端口，并继续拒绝私网、localhost 和字面量 IP 目的地址。
- API、Worker 与 Runner 使用 Compose DNS 互联，不通过宿主机端口绕行。

## 数据和停止

- PostgreSQL、RabbitMQ、MinIO 使用环境栈的 Compose 项目作用域卷；本地和生产应用栈使用各自的工作卷，不共享数据卷。
- Runner 与下载 Worker 共享的工作卷只保存单任务临时文件；成功上传或失败后均应清理。
- 常规停止分别使用对应入口的 `docker compose -f <文件> down`；不得在未确认备份时添加 `--volumes`。生产应用使用 `docker-compose-prod.yml`，本地基础设施使用 `docker-compose-env.yml`。
- `.env`、用户 URL、Cookie、Authorization、provider key 和完整模型输出不得进入日志或提交。

## 最小检查

```bash
curl --fail http://localhost:8101/health/live
curl --fail http://localhost:8101/health/ready
docker compose -f docker-compose.yml ps
```

若下载解析失败，先区分 URL/格式业务错误、Runner 健康、egress ACL、队列积压和对象存储，不要通过开放私网、上传 Cookie 或透传 yt-dlp 参数绕过控制。
