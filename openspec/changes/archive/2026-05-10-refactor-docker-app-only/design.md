## Context

用户希望 Docker 容器仅承载应用逻辑，而数据库等重型基础设施保持在宿主机（Homebrew 安装）或独立管理。

## Goals / Non-Goals

**Goals:**
- 默认 `docker-compose.yml` 只运行应用。
- 容器通过 `host.docker.internal` 访问宿主机服务。
- 保持生产环境 `prod.yml` 为全量镜像（包括基础设施），确保部署一致性。

**Non-Goals:**
- 不再在 `docker-compose.yml` 中定义 `postgres`, `redis`, `minio` 容器。

## Decisions

### 1. 默认 Compose 指向宿主机
- 在 `docker-compose.yml` 中为 `api` 和 `worker` 添加 `extra_hosts`：
  ```yaml
  extra_hosts:
    - "host.docker.internal:host-gateway"
  ```
- 环境变量引用：
  - `DATABASE_URL`: `${DOCKER_DATABASE_URL}`
  - `REDIS_URL`: `${DOCKER_REDIS_URL}`
  - `S3_ENDPOINT_URL`: `${DOCKER_S3_ENDPOINT_URL}`

### 2. 文件夹结构
- `docker-compose.yml`: API, Worker, Web (App Only).
- `docker-compose.prod.yml`: API, Worker, Web + PostgreSQL, Redis, MinIO (Full Stack).

## Risks / Trade-offs

- **[Risk] 宿主机服务未启动** → **[Mitigation]** 容器启动会报错，需在 `README` 明确提示先启动 Homebrew 服务。
- **[Risk] 端口冲突** → **[Mitigation]** 使用环境变量控制端口映射，默认保持 API:8000, Web:3000。
