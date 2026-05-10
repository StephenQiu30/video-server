## Why

当前 Docker 配置分散在 `infra/docker` 目录下，文件命名不统一且存在冗余，导致维护困难（过度设计）。为了遵循“极简”原则，需要将所有 Docker 相关文件移至根目录进行统一管理，并简化 Dockerfile 逻辑，同时明确 `docker-compose.yml` (基础基础设施) 与 `docker-compose.prod.yml` (全量生产环境) 的职责。

## What Changes

- **位置迁移**：将 `infra/docker/` 下的所有文件移出，并在根目录重新组织。
- **Dockerfile 整合**：
    - 创建根目录 [Dockerfile](file:///Users/stephenqiu/Desktop/StephenQiu30/Video/Dockerfile)，使用多阶段构建（multi-stage）同时支持 API、Worker 和 Web 生产镜像。
- **Compose 职责划分**：
    - [docker-compose.yml](file:///Users/stephenqiu/Desktop/StephenQiu30/Video/docker-compose.yml)：默认用于本地开发，仅包含 Database, Redis, MinIO 等基础设施，方便开发者直接在宿主机运行代码。
    - [docker-compose.prod.yml](file:///Users/stephenqiu/Desktop/StephenQiu30/Video/docker-compose.prod.yml)：用于一键部署全量服务（API, Worker, Web + Infra），采用生产环境配置。
- **清理冗余**：删除 `infra/` 目录下过时的 Docker 配置。

## Capabilities

### New Capabilities
- 无

### Modified Capabilities
- `project-runtime-foundation`: 优化环境启动与容器化标准。

## Impact

- **部署流程**：开发者现在可以在根目录直接运行 `docker compose up -d` 启动基础服务。
- **镜像构建**：统一使用根目录的单 `Dockerfile` 进行构建。
- **配置文件**：统一挂载根目录的 `.env` 文件。
