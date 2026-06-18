# centralized-runtime

## Description

单进程中心化运行时，在同一容器/进程中同时运行 FastAPI API server 和 RQ queue consumer。

## Requirements

- `apps/api/app/runtime.py` SHALL 作为唯一业务入口点
- 主进程 SHALL 运行 uvicorn API server
- 子线程 SHALL 启动 RQ Worker（支持 SimpleWorker 和 Worker 模式）
- Worker 线程 SHALL 在 API server 关闭时优雅退出
- `python -m app.runtime` SHALL 启动完整服务（API + 队列消费者）
- 环境变量 `API_HOST`、`API_PORT` SHALL 控制 API 绑定地址
- 环境变量 `RQ_WORKER_MODE` SHALL 控制 Worker 类型（默认 fork）

## Scenarios

### Success Path

1. `python -m app.runtime` 启动
2. 主线程初始化 uvicorn API server
3. 子线程启动 RQ Worker 监听 `downloads` 队列
4. API 接收请求，任务通过 Redis Queue 入队
5. 同一进程内 Worker 线程消费任务并执行下载
6. 接收到 SIGTERM 信号时，Worker 线程先停止，API server 后关闭

### Failure Path

1. Redis 连接失败：Worker 线程退出，API 继续运行，`/ready` 报告 queue_consumer 异常
2. Worker 线程未启动：`/ready` 报告 queue_consumer 未就绪
3. API server 启动失败：进程退出码非零

## Validation Evidence

- `pytest apps/api/tests/test_health.py -v` 验证 queue_consumer 检查
- `pytest apps/api/tests/test_architecture_boundaries.py -v` 验证架构边界
- `python -m app.runtime --help` 验证入口可用
- Docker `docker compose config` 验证单 service 结构
