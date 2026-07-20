# Docker 部署操作

服务端只维护三种 Compose 用法：默认完整环境、`prod` 覆盖和仅 PostgreSQL/RabbitMQ/MinIO 的依赖环境。所有地址、端口和凭据均来自 `.env`，生产值不得提交。

## 默认完整环境

```powershell
Copy-Item .env.example .env
# 修改 .env 中所有 replace-with-* 值
docker compose config --quiet
docker compose up -d --build
docker compose ps
```

默认编排固定为 API、download worker、PostgreSQL、RabbitMQ 和 MinIO 五个单元。API 在启动前执行 `alembic upgrade head`；Worker 等待 API readiness 通过后再启动。

停止服务使用 `docker compose down`。除非明确要删除业务数据，不得附加 `--volumes`。

## 仅启动基础设施

```powershell
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose-env.yml ps
```

该模式供宿主机直接运行 API、Worker 和 Alembic。`.env` 中的 `DATABASE_URL`、`RABBITMQ_URL`、`MINIO_ENDPOINT` 指向 `localhost`；完整容器环境使用对应的 `COMPOSE_*` 地址，不需要手工切换。

## prod 环境

```powershell
Copy-Item .env.prod.example .env.prod
# 替换域名、镜像和全部 Secret，并确保 URL 中密码已做 URL 编码
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml up -d
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose-prod.yml ps
```

`prod` 只覆盖镜像拉取和重启策略，服务拓扑与默认环境完全一致。外部 TLS、域名和入口代理由部署平台负责；MinIO API 与 Console 默认只绑定回环地址。

## 健康检查与回滚

- API：`GET /health/live` 与 `GET /health/ready`。
- PostgreSQL：`pg_isready`；RabbitMQ：`rabbitmq-diagnostics ping`；MinIO：`/minio/health/live`。
- 回滚时将 `.env.prod` 的 `VIDEO_SERVER_IMAGE` 改为已验证的旧版本标签，再重复 prod 启动命令。数据库迁移必须使用已验证可兼容该版本的 revision；不得通过删除受控卷回滚。
