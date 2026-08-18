# 根目录 Compose 运行手册

## 运行模型

仓库提供三种明确的 Compose 拓扑：

| 文件 | 用途 | 是否启动 PostgreSQL、RabbitMQ、Valkey、MinIO |
| --- | --- | --- |
| docker-compose-env.yml | 本项目专用基础环境 | 是，仅启动 PostgreSQL、RabbitMQ、Valkey、MinIO |
| docker-compose.yml | 本机/共享环境运行，只启动业务容器 | 否，复用宿主机已有服务 |
| docker-compose-prod.yml | 独立的生产业务容器运行配置，与默认拓扑保持一致 | 否，复用生产宿主机服务 |

默认业务拓扑包含 API、Outbox、下载 Worker、导入 Worker、报告 Worker、Provider Canary、Media Runner 和受控出口代理。YouTube Operator 与其他 Provider Operator 只通过对应 profile 显式启用。

Compose 文件不再通过 YAML Anchor 隐式继承服务配置；每个服务直接声明自己的角色、连接地址、挂载、网络和启动命令。

## 宿主机基础设施

不启动 docker-compose-env.yml 时，使用 docker-compose.yml 或 docker-compose-prod.yml 前，宿主机必须已经提供：

- PostgreSQL
- RabbitMQ
- Valkey/Redis
- MinIO

容器通过 host.docker.internal 访问这些服务。生产环境的连接地址和凭据只放在本地 .env.prod，不能提交到 Git。

## 本机业务拓扑

~~~bash
cp .env.example .env
docker compose --env-file .env -f docker-compose-env.yml config --quiet
docker compose --env-file .env -f docker-compose.yml config --quiet
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose.yml up -d --build
~~~

访问地址：

- Web/API：http://localhost:8101
- Swagger UI：http://localhost:8101/docs
- OpenAPI：http://localhost:8101/openapi.json

如果只需要容器内的受控出口代理：

~~~bash
docker compose --env-file .env -f docker-compose.yml up -d egress-proxy
~~~

## 完整隔离环境

项目专用基础环境可独立启动，随后由业务 Compose 复用：

~~~bash
cp .env.example .env
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose.yml up -d --build
~~~

项目专用环境与本机已有同端口服务不要同时运行，避免端口冲突；业务 Compose 不会自动启动基础环境。

## 生产环境

.env.prod 只允许由部署者在本机或 Secret 管理系统生成。仓库中的 .env.prod.example 只包含占位值。

~~~bash
cp .env.prod.example .env.prod
# 替换全部 replace-with-* 占位值
docker compose --env-file .env.prod -f docker-compose-prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose-prod.yml up -d --no-build
~~~

生产镜像必须先以 video-server:prod 的名称加载或发布。生产 Compose 不启动基础设施初始化服务，也不包含 environment profile。

生产健康检查：

~~~bash
curl --fail http://127.0.0.1:8101/health/live
curl --fail http://127.0.0.1:8101/health/ready
~~~

## AI Worker

AI Worker 继续运行在宿主机，不由 Compose 启动：

~~~bash
cd backend
uv run --env-file ../.env.prod python -m app.workers.analysis.main
~~~

启用 ANALYSIS_ENABLED=true 时，API 只有在兼容 Worker 心跳有效后才会就绪。没有宿主机 AI Worker 时，设置 ANALYSIS_ENABLED=false 后重建 API。

## Operator Profile

YouTube 受控会话：

~~~bash
docker compose --env-file .env.prod -f docker-compose-prod.yml --profile youtube-operator config --quiet
docker compose --env-file .env.prod -f docker-compose-prod.yml --profile youtube-operator up -d --no-build
~~~

其他受控 Provider：

~~~bash
docker compose --env-file .env.prod -f docker-compose-prod.yml --profile provider-operator up -d --no-build
~~~

启用前必须按对应 Provider 运维手册完成 Cookie、权限、固定出口和授权 canary 门禁。

## 停止和数据安全

~~~bash
docker compose --env-file .env.prod -f docker-compose-prod.yml down
~~~

不要在未确认备份的情况下使用 --volumes。 .env、.env.prod、Cookie、Authorization、Provider key 和完整模型输出不得进入日志或 Git。
