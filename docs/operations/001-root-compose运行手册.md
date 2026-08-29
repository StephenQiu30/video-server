# 根目录 Compose 运行手册

## 运行模型

完整项目只有一个运行入口：根目录 `docker-compose.yml`。其余 Compose 文件负责
基础依赖或生产差异，不是本机项目的平行启动入口：

| 文件 | 用途 | 是否启动 PostgreSQL、RabbitMQ、Valkey、MinIO |
| --- | --- | --- |
| docker-compose-env.yml | 本项目专用基础环境 | 是，仅启动 PostgreSQL、RabbitMQ、Valkey、MinIO |
| docker-compose.yml | 本机/共享环境运行，只启动业务容器 | 否，复用宿主机已有服务 |
| docker-compose-prod.yml | 独立的生产业务容器运行配置，与默认拓扑保持一致 | 否，复用生产宿主机服务 |

默认业务拓扑包含 API、Outbox、下载 Worker、导入 Worker、报告 Worker、Provider Canary、Media Runner 和受控出口代理。YouTube Operator 与其他 Provider Operator 只通过对应 profile 显式启用。

Compose 文件不再通过 YAML Anchor 隐式继承服务配置；每个服务直接声明自己的角色、连接地址、挂载、网络和启动命令。

## Docker 文件使用规范

- `docker-compose-env.yml` 只部署本项目专用的 PostgreSQL、RabbitMQ、Valkey 和 MinIO，并负责一次性初始化；`docker-compose.yml` 只部署业务容器；`docker-compose-prod.yml` 只提供生产业务容器差异。
- 业务 Compose 通过 `POSTGRES_HOST/PORT`、`RABBITMQ_HOST/PORT`、`VALKEY_HOST/PORT` 和 `MINIO_HOST/PORT` 连接基础服务。启动 `docker-compose-env.yml` 时使用服务名和容器端口；复用已有基础服务时改为宿主机可达地址和已发布端口。
- `HOST_*_PORT` 仅用于环境 Compose 向宿主机发布端口，不是业务容器的连接端口。不要把两类端口混用。
- MinIO 只配置一组 `MINIO_ACCESS_KEY` 与 `MINIO_SECRET_KEY`，所有业务进程共用；不要按 API、导入、下载、报告或分析进程复制密钥变量。
- CI、开发和本机验收必须复用上述正式 Compose 文件，不新增仅供某个环境的覆盖文件。

## 宿主机基础设施

不启动 docker-compose-env.yml 时，使用 docker-compose.yml 或 docker-compose-prod.yml 前，宿主机必须已经提供：

- PostgreSQL
- RabbitMQ
- Valkey/Redis
- MinIO

容器通过 `.env` 中的连接地址访问这些服务。生产环境的连接地址和凭据只放在本地 .env.prod，不能提交到 Git。

## 本机业务拓扑

~~~bash
cp .env.example .env
docker compose --env-file .env -f docker-compose-env.yml config --quiet
docker compose --env-file .env -f docker-compose.yml config --quiet
# 首次使用或基础依赖尚未运行时执行一次
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
~~~

最后一条 Docker Compose 命令是本机完整项目的启动与重启入口。它统一构建前端与
后端镜像、重新创建业务服务并等待健康检查。需要 Operator Runner 时，在 `.env` 的
`COMPOSE_PROFILES` 中声明与 `RUNNER_OPERATOR_BASE_URLS` 一致的 profile。项目启动
不会启动宿主机浏览器或 Session Broker。不要使用不会应用代码、镜像或配置变化的
`docker compose restart`。

访问地址：

- Web：http://localhost:8101
- API/Swagger UI：http://localhost:8111/docs
- OpenAPI：http://localhost:8111/openapi.json

如果只需要容器内的受控出口代理：

~~~bash
docker compose --env-file .env -f docker-compose.yml up -d egress-proxy
~~~

## 完整隔离环境

项目专用基础环境只需在首次使用或依赖未运行时准备一次，随后由唯一业务 Compose
入口复用：

~~~bash
cp .env.example .env
docker compose --env-file .env -f docker-compose-env.yml up -d
docker compose --env-file .env -f docker-compose.yml up -d --build --force-recreate --remove-orphans --wait --wait-timeout 300
~~~

代码同步与服务启动保持解耦；需要更新时先执行：

~~~bash
git pull --ff-only
~~~

随后执行上面的唯一业务 Compose 命令。YouTube、TikTok、X 完整媒体 Canary 属于
启动后的验收步骤，不与项目生命周期耦合；命令见
`docs/operations/007-固定Provider探针运行手册.md`。

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
curl --fail http://127.0.0.1:8111/health/live
curl --fail http://127.0.0.1:8111/health/ready
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
