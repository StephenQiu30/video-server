## Context

目前项目的 Docker 配置存在路径深、文件散、职责不清的问题。特别是在本地开发时，往往只需要启动数据库等中间件，而目前的 `docker-compose` 默认尝试构建全量镜像，增加了启动开销。

## Goals / Non-Goals

**Goals:**
- 将所有 Docker 配置统一收拢至根目录。
- 使用一个 `Dockerfile` 通过 `--target` 区分不同服务，保持镜像定义简洁。
- 明确 Compose 环境：`yml` 提供基础环境，`prod.yml` 提供完整堆栈。

**Non-Goals:**
- 不再维护 `infra/docker` 目录。
- 不引入复杂的 Kubernetes 或 Helm 配置（保持极简）。

## Decisions

### 1. 多阶段单一 Dockerfile
**选择：在根目录维护一个 `Dockerfile`**
- **理由**：API、Worker 和 Web 的构建逻辑可以互补（特别是 Python 两个服务）。通过 `FROM ... AS` 语法，可以用一个文件管理所有镜像，减少代码碎片。

### 2. Compose 职责分离
- **`docker-compose.yml` (Default)**: 
    - 包含：`db`, `redis`, `minio`。
    - 场景：本地开发。开发者运行 `docker compose up` 即可启动所有依赖项。
- **`docker-compose.prod.yml`**:
    - 包含：`api`, `worker`, `web` + 依赖。
    - 场景：生产部署或本地全流程集成测试。

### 3. 环境与挂载
- 统一挂载 `./.env` 到容器内部。
- 保持 `host.docker.internal` 映射，确保容器能正确访问宿主机网络。

## Risks / Trade-offs

- **[Risk] Dockerfile 变得过大** → **[Mitigation]** 保持各阶段逻辑独立，使用 `.dockerignore` 排除 `node_modules` 和 `__pycache__` 等无关文件。
- **[Risk] 破坏现有 CI 流程** → **[Mitigation]** 迁移后需同步更新 `.github/workflows/` 中的路径引用。
