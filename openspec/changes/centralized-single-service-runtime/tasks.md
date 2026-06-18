# Tasks: 中心化单服务运行时

## Task 1: 创建中心化 runtime 入口

**Files**: `apps/api/app/runtime.py`
**Validation**: `python -c "from app.runtime import main; print('import ok')"`

- [x] 1.1 创建 `apps/api/app/runtime.py`
- [x] 1.2 在子线程中启动 RQ Worker（daemon=True）
- [x] 1.3 主线程运行 uvicorn API server
- [x] 1.4 全局标志 `_worker_ready` 追踪 Worker 线程状态
- [x] 1.5 支持 `API_HOST`、`API_PORT`、`RQ_WORKER_MODE` 环境变量

## Task 2: 更新 Dockerfile 为单 target

**Files**: `Dockerfile`
**Validation**: `docker build --target app -t video-server-app .`

- [x] 2.1 移除 `api` 和 `worker` 两个 target
- [x] 2.2 创建 `app` target，安装 api + worker 依赖
- [x] 2.3 CMD 改为 `python -m app.runtime`

## Task 3: 更新 docker-compose.yml 为单 service

**Files**: `docker-compose.yml`
**Validation**: `docker compose config`

- [x] 3.1 移除 `api` 和 `worker` service
- [x] 3.2 创建 `app` service，target: app
- [x] 3.3 healthcheck 使用 `/ready` 端点

## Task 4: 更新 docker-compose.prod.yml

**Files**: `docker-compose.prod.yml`
**Validation**: `docker compose -f docker-compose.yml -f docker-compose.prod.yml config`

- [x] 4.1 移除 `api` 和 `worker` service
- [x] 4.2 创建 `app` service，合并环境变量和依赖
- [x] 4.3 保留 postgres、redis、minio 基础设施 service

## Task 5: 更新 /ready 端点增加 queue_consumer 检查

**Files**: `apps/api/app/routers/health.py`
**Validation**: `pytest apps/api/tests/test_health.py -v`

- [x] 5.1 新增 `_check_queue_consumer()` 函数
- [x] 5.2 读取 `app.runtime._worker_ready` 全局标志
- [x] 5.3 将 `queue_consumer` 加入 `/ready` checks

## Task 6: 更新启动脚本

**Files**: `scripts/start.sh`
**Validation**: `bash -n scripts/start.sh`

- [x] 6.1 移除 `worker` 和 `local:worker` 模式
- [x] 6.2 `local` 模式启动中心化 runtime
- [x] 6.3 Docker 模式只启动 `app` service

## Task 7: 创建计划文档

**Files**: `docs/plans/15-中心化单服务运行时修复计划.md`
**Validation**: 文件存在且内容完整

- [x] 7.1 记录目标、变更范围、验收标准

## Task 8: 更新 README

**Files**: `README.md`
**Validation**: `grep -q "app" README.md`

- [x] 8.1 更新快速开始说明
- [x] 8.2 更新 Docker 部署说明
- [x] 8.3 更新常用命令

## Task 9: 运行验收测试

**Validation**:

```bash
bash scripts/validate-repository.sh
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_architecture_boundaries.py -v
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_health.py -v
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_worker_jobs.py -v
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_task_endpoints.py -v
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_openapi_contract.py -v
```
