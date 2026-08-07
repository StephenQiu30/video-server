# 根目录 Compose 运行手册

## 三个固定入口

| 文件 | 职责 |
| --- | --- |
| `docker-compose.yml` | 完整系统：API/同源前端、Outbox、下载与 AI Worker、Media Runner、egress proxy、PostgreSQL、RabbitMQ、MinIO |
| `docker-compose-env.yml` | 仅启动 PostgreSQL、RabbitMQ、MinIO 及 MinIO 初始化器，供宿主机开发 |
| `docker-compose-prod.yml` | 生产覆盖；叠加默认完整系统使用 |

仓库不使用 `deploy/` 目录。Compose 文件只声明服务编排、容器名、端口、卷和 env 文件引用；环境变量的具体值只写在 `.env.example`、`.env.prod.example` 或被 Git 忽略的 `.env*` 文件中。

## 完整启动

```bash
cp .env.example .env
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up -d --build
```

入口为 <http://localhost:8101>。Swagger UI 位于 <http://localhost:8101/docs>，OpenAPI 契约位于 <http://localhost:8101/openapi.json>。API 固定绑定 `127.0.0.1:8101`；MinIO API 与控制台固定绑定 `127.0.0.1:19190/19191`。

所有服务都显式声明 `container_name`，容器名稳定为 `video-server-api`、`video-server-postgres` 等，不会出现 `xxx-1` 副本后缀。默认完整启动读取被 Git 忽略的 `.env`，首次启动前从 `.env.example` 复制。

## 仅依赖环境

```bash
cp .env.example .env
docker compose -f docker-compose-env.yml config --quiet
docker compose -f docker-compose-env.yml up -d
```

此模式不会启动 API、Worker、Runner 或前端构建。固定宿主机端口为：PostgreSQL `localhost:15432`、RabbitMQ `localhost:5673`（管理台 `15673`）、MinIO `localhost:19190`（控制台 `19191`）。

## 生产覆盖

```bash
cp .env.prod.example .env.prod
# 替换 .env.prod 中全部 replace-with-* 占位值
docker compose -f docker-compose.yml -f docker-compose-prod.yml config --quiet
docker compose -f docker-compose.yml -f docker-compose-prod.yml up -d --build
```

生产覆盖文件只切换 env 文件和重启策略，不在 Compose 中填写密码、密钥、连接地址或 Provider Key。生产运行前必须替换 `.env.prod` 中的占位值。

## 网络边界

- 服务使用 Compose 默认网络互联，不额外维护命名网络。
- Media Runner 通过 egress proxy 访问外部媒体地址；proxy 不暴露宿主机端口，并继续拒绝私网、localhost 和字面量 IP 目的地址。
- API、Worker 与 Runner 使用 Compose DNS 互联，不通过宿主机端口绕行。

## 数据和停止

- PostgreSQL、RabbitMQ、MinIO 使用 Compose 项目作用域卷；完整环境与仅依赖环境分别属于不同栈，不共享数据卷。
- Runner 与下载 Worker 共享的工作卷只保存单任务临时文件；成功上传或失败后均应清理。
- 常规停止使用 `docker compose -f docker-compose.yml down` 或 `docker compose -f docker-compose-env.yml down`；不得在未确认备份时添加 `--volumes`。
- `.env`、用户 URL、Cookie、Authorization、provider key 和完整模型输出不得进入日志或提交。

## 最小检查

```bash
curl --fail http://localhost:8101/health/live
curl --fail http://localhost:8101/health/ready
docker compose -f docker-compose.yml ps
```

若下载解析失败，先区分 URL/格式业务错误、Runner 健康、egress ACL、队列积压和对象存储，不要通过开放私网、上传 Cookie 或透传 yt-dlp 参数绕过控制。
