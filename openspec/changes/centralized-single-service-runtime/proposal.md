## Why

当前 Dockerfile、docker-compose、启动脚本和代码入口仍然维持 `api` 与 `worker` 两个独立业务 target/service。对个人自部署场景，这导致需要管理两个容器生命周期、两次镜像构建、两套健康检查，且无法在单进程内保证队列消费者与 API 同生命周期。本 change 将 video-server 收敛为一个中心化单服务运行时。

## What Changes

- 创建 `apps/api/app/runtime.py` 作为中心化入口：在子线程中启动 RQ Worker，主进程运行 uvicorn API server
- Dockerfile 合并为单个业务 target `app`，安装 api + worker 全部依赖
- docker-compose.yml 和 docker-compose.prod.yml 将 `api` + `worker` 合并为单个 `app` service
- `/ready` 端点增加 `queue_consumer` 检查，验证嵌入式 Worker 线程是否存活
- 移除 `scripts/start.sh` 中独立 worker 启动路径
- 更新 README 和 operations 文档反映单服务架构

## Capabilities

### New Capabilities

- `centralized-runtime`: 单进程同时运行 API server 和 RQ queue consumer
- `queue-consumer-health`: `/ready` 端点检查嵌入式队列消费者存活状态

### Modified Capabilities

- `async-download-task-flow`: 入口从独立 worker 容器改为 app 容器内嵌线程

## Impact

- `apps/api/app/runtime.py` — 新建，中心化入口
- `Dockerfile` — 合并 api/worker 为单 target `app`
- `docker-compose.yml` — 合并 api/worker service 为 `app`
- `docker-compose.prod.yml` — 同上
- `scripts/start.sh` — 移除独立 worker 模式
- `apps/api/app/routers/health.py` — 增加 queue_consumer 检查
- `README.md` — 更新部署说明
- `docs/plans/15-中心化单服务运行时修复计划.md` — 新建计划文档
