# 中心化单服务运行时设计

## Goals

- 个人自部署场景下，一个容器即完整业务服务
- 消除 api/worker 双容器管理复杂度
- 保持 Redis/RQ 内部队列机制不变

## Non-Goals

- 不移除 Redis/RQ，不改为同步执行
- 不引入 Kubernetes 多副本调度
- 不改造前端页面

## Architecture

```
┌─────────────────────────────────────────────┐
│  app container (single process)             │
│                                             │
│  ┌───────────────┐  ┌──────────────────┐    │
│  │  uvicorn       │  │  RQ Worker       │    │
│  │  (main thread) │  │  (daemon thread) │    │
│  │  FastAPI :8000 │  │  downloads queue │    │
│  └───────┬───────┘  └────────┬─────────┘    │
│          │                   │              │
│          └───────┬───────────┘              │
│                  │                          │
│          ┌───────▼───────┐                  │
│          │  Redis / RQ   │                  │
│          └───────────────┘                  │
└─────────────────────────────────────────────┘
         │              │              │
    ┌────▼────┐   ┌─────▼─────┐  ┌────▼────┐
    │Postgres │   │   Redis   │  │  MinIO  │
    └─────────┘   └───────────┘  └─────────┘
```

## Contracts

### runtime.py 入口

- `main()` 函数作为唯一入口
- 使用 `threading.Thread(daemon=True)` 启动 RQ Worker
- Worker 线程运行 `worker.main` 模块的 `main()` 函数
- 主线程运行 `uvicorn.run(app, host, port)`
- SIGTERM/SIGINT 时，先设置停止标志让 Worker 线程退出

### Dockerfile

- 单一业务 target `app`
- 安装 api + worker 的 requirements.txt
- COPY apps/api、apps/worker、packages
- CMD: `python -m app.runtime`

### docker-compose.yml

- 单业务 service `app`（替代 api + worker）
- 基础设施 service 不变：postgres、redis、minio
- healthcheck 使用 `/ready` 端点

### /ready 端点

- 新增 `queue_consumer` 检查项
- 验证 Worker 线程存活状态（通过全局标志或线程引用）

## State Flow

1. 容器启动 → `python -m app.runtime`
2. runtime.main() 初始化
3. 创建 RQ Worker 线程（daemon=True）
4. 启动 Worker 线程
5. 启动 uvicorn（主线程阻塞）
6. Worker 线程消费队列任务
7. 收到 SIGTERM → uvicorn 退出 → 主线程退出 → daemon 线程自动终止

## Failure Paths

| 场景 | 行为 |
|------|------|
| Redis 不可用 | Worker 线程启动失败，API 正常运行，/ready 报告 degraded |
| Postgres 不可用 | API 启动失败（lifespan 检查），进程退出 |
| Worker 线程崩溃 | daemon 线程退出，API 继续运行，/ready 报告 degraded |
| yt-dlp 依赖缺失 | Worker 任务失败，API 正常运行 |

## Rollback Impact

- 回滚只需恢复 Dockerfile 和 compose 文件的双 target/service 结构
- runtime.py 为新增文件，删除即可
- 数据库和 Redis 无 schema 变更
