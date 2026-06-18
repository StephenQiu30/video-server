## Why

当前项目把 API 与 Worker 表达为两个代码入口（`apps/api/app/main.py` 和 `apps/worker/worker/main.py`）、两个 Docker target（`api` 和 `worker`）和两个 Compose 业务服务（`api` 和 `worker`），增加个人自部署场景的部署和排障成本。本次变更以 PRD10 为需求源，定义中心化单服务运行时，使 Docker 一键启动一个 `app` 容器即可同时运行 API、队列消费、下载执行和 MinIO/S3 交付。

## What Changes

- 定义单业务服务 `app`：Compose 中只有一个业务服务，代码层只有一个部署入口（中心化 runtime）。
- 定义消息队列内部化：Redis/RQ 保留为同一项目内部机制，不作为独立业务服务暴露。
- 定义 MinIO/S3 唯一最终交付：本地路径禁止泄漏到 API/DB/分享链接。
- 定义 readiness 规则：`/ready` 必须覆盖 API、队列消费者、下载执行器和对象存储全部组件。
- 收敛 Dockerfile 和 Compose：从两个 target + 两个服务收敛为一个 target + 一个服务。

## Capabilities

### New Capabilities

- `centralized-single-service-runtime`: 定义中心化单服务运行时需求，包括单入口、单 Compose 服务、队列内部化、MinIO 交付和 readiness 规则。
- `compose-convergence`: 定义 Dockerfile 从多 target 收敛为单 target、Compose 从多业务服务收敛为单 `app` 服务的规则。
- `local-path-isolation`: 定义本地临时路径禁止泄漏到 API/DB/分享链接的边界。

### Modified Capabilities

- `self-host-runtime`: PRD05 中定义的双服务部署模式需要更新为单服务模式。
- `minio-artifact-archive`: MinIO/S3 作为唯一最终交付入口的约束需要与 PRD10 对齐。

## Impact

- **新增文档**: `docs/prd/10-中心化单服务运行时.md`、`docs/design/03-中心化单服务架构重评审.md`、`docs/acceptance/03-中心化单服务与MinIO交付验收标准.md`
- **索引更新**: `docs/prd/README.md`、`docs/design/README.md`、`docs/acceptance/README.md`、`docs/README.md`
- **新增 OpenSpec change**: `openspec/changes/centralized-single-service-runtime/`
- **下游影响**: PLAN15 子任务将执行 Dockerfile/Compose 收敛和代码入口合并
- **依赖**: 无新增外部依赖
