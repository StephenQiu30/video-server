# 根目录 Compose 运行手册

## 两个固定入口

| 文件 | 职责 |
| --- | --- |
| `docker-compose.yml` | 完整系统：API/同源前端、Outbox、下载与 AI Worker、Media Runner、egress proxy、PostgreSQL、RabbitMQ、MinIO |
| `docker-compose-env.yml` | 仅启动 PostgreSQL、RabbitMQ、MinIO 及 MinIO 初始化器，供宿主机开发 |

仓库不使用 `deploy/` 目录，也不维护没有明确目标的生产覆盖 Compose。需要覆盖本地密码、对象存储公开地址或 AI Provider 时，复制 `.env.example` 为 `.env`；普通本地启动无需 `.env`。

## 完整启动

```bash
docker compose -f docker-compose.yml config --quiet
docker compose -f docker-compose.yml up -d --build
```

入口为 <http://localhost:8101>。Swagger UI 位于 <http://localhost:8101/docs>，OpenAPI 契约位于 <http://localhost:8101/openapi.json>。API 固定绑定 `127.0.0.1:8101`；MinIO API 与控制台固定绑定 `127.0.0.1:19190/19191`。

默认文本模型配置指向宿主机已有的 Ollama 服务与 `deepseek-r1:8b`，项目不会安装 Ollama 或拉取模型；运行环境应确保容器可访问 `host.docker.internal:11434`。切换云端 DeepSeek 时设置 `ANALYSIS_PROVIDER=deepseek` 和 `DEEPSEEK_API_KEY`。真实视频分析还需要独立的 `OPENAI_API_KEY` 执行音频转录。

PostgreSQL 在全新数据卷首次启动时以单事务执行 `backend/sql/schema.sql`，健康检查同时验证关键业务表。项目不提供旧数据卷升级兼容，schema 变化后应使用新数据卷验证。

## 仅依赖环境

```bash
docker compose -f docker-compose-env.yml config --quiet
docker compose -f docker-compose-env.yml up -d
```

此模式不会启动 API、Worker、Runner 或前端构建。固定宿主机端口为：PostgreSQL `localhost:15432`、RabbitMQ `localhost:5673`（管理台 `15673`）、MinIO `localhost:19190`（控制台 `19191`）。这些地址也是后端类型化配置的本地默认值。

仅依赖栈容器名为 `video-server-dev-postgres`、`video-server-dev-rabbitmq`、`video-server-dev-minio` 和一次性 `video-server-dev-minio-init`。如本机已运行这些依赖，不需要启动该栈；在被 Git 忽略的根 `.env` 中只设置与默认值不同的 `DATABASE_URL`、`RABBITMQ_URL`、`MINIO_ENDPOINT` 和对应凭据。

## 网络边界

- 所有服务连接到一个明确命名的 `video-server-network`。
- Media Runner 仍通过 egress proxy 访问外部媒体地址；proxy 不暴露宿主机端口，并继续拒绝私网、localhost 和字面量 IP 目的地址。
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
