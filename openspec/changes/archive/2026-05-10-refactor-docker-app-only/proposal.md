## Why

根据用户反馈，本地开发环境（PostgreSQL, Redis, MinIO）已通过 Homebrew 或独立 Docker 容器运行，因此 `docker-compose.yml` 不应重复启动这些基础设施服务。相反，Compose 应专注于启动 **应用容器（API, Worker, Web）**，并正确连接到宿主机上的已有服务，以实现轻量化运行并避免资源冲突。

## What Changes

- **Compose 职责调整**：
    - 将 [docker-compose.yml](file:///Users/stephenqiu/Desktop/StephenQiu30/Video/docker-compose.yml) 调整为仅包含应用服务（`api`, `worker`, `web`），默认连接宿主机基础设施。
    - 引入 `extra_hosts` 配置，确保容器内部可以通过 `host.docker.internal` 访问宿主机服务。
- **基础设施配置解耦**：
    - 创建 `docker-compose.infra.yml`（可选），保留原有的基础设施启动逻辑，仅在需要纯净隔离环境时使用。
- **环境配置优化**：
    - 确保应用容器优先读取 `DOCKER_DATABASE_URL` 等变量。

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- `project-runtime-foundation`: 优化 Docker 运行模式，支持连接宿主机基础设施。

## Impact

- **启动效率**：`docker compose up` 现在仅启动应用代码，速度更快。
- **兼容性**：完美适配用户已有的 Homebrew 环境。
- **配置**：继续沿用根目录 `.env`。
