# 设计：中心化单服务运行时

## 1. 目标

以 PRD10 为需求源，定义中心化单服务运行时的技术边界，覆盖单入口、单 Compose 服务、队列内部化、MinIO 交付和 readiness 规则。

## 2. 非目标

1. 不移除 Redis/RQ。
2. 不让 API 同步执行长耗时下载。
3. 不把本地目录作为最终交付方式。
4. 不引入 Kubernetes 或多服务编排。
5. 不在本变更中执行代码改动（代码改动由 PLAN15 子任务执行）。

## 3. 架构决策

### 3.1 单入口 runtime

```text
                    ┌─────────────────────────────────┐
                    │           app (单容器)            │
                    │                                   │
                    │  ┌─────────┐  ┌───────────────┐  │
                    │  │ FastAPI  │  │ RQ Worker Loop │  │
                    │  │  :8000   │  │  (消费队列)     │  │
                    │  └─────────┘  └───────────────┘  │
                    │                                   │
                    │  共享：Python runtime、依赖库、     │
                    │  数据库连接、Redis 连接、S3 客户端  │
                    └─────────────────────────────────┘
                              │           │
                    ┌─────────┴───┐  ┌────┴────┐
                    │  PostgreSQL │  │  Redis   │
                    │   (独立容器) │  │ (独立容器)│
                    └─────────────┘  └─────────┘
```

### 3.2 Compose 收敛

```yaml
# 收敛后
services:
  app:
    build:
      context: .
      target: app          # 单 target
    # ... 环境变量、端口、健康检查

  postgres:
    # ... 基础设施，不变

  redis:
    # ... 基础设施，不变

  minio:
    # ... 基础设施，不变
```

### 3.3 Dockerfile 收敛

```dockerfile
# 收敛后
FROM python-base AS app
COPY apps/api/requirements.txt /app/apps/api/requirements.txt
COPY apps/worker/requirements.txt /app/apps/worker/requirements.txt
RUN pip install --no-cache-dir \
    -r /app/apps/api/requirements.txt \
    -r /app/apps/worker/requirements.txt
COPY apps/api /app/apps/api
COPY apps/worker /app/apps/worker
COPY packages /app/packages
EXPOSE 8000
CMD ["python", "-m", "app.runtime"]  # 中心化 runtime 入口
```

## 4. 数据流

```text
用户分享 URL
  → /api/parse (FastAPI)
  → /api/tasks (FastAPI, 创建任务写入 DB)
  → RQ enqueue (Redis)
  → RQ Worker (app 内部消费)
  → yt-dlp 下载 + FFmpeg 合并
  → 临时文件存放在容器内部 /tmp
  → 上传到 MinIO/S3
  → 写入 presigned_url 到 DB
  → 清理临时文件
  → 用户通过 presigned_url 下载
```

## 5. 失败路径

1. 数据库不可用 → `/ready` 返回 503，`db: fail`。
2. Redis 不可用 → `/ready` 返回 503，`redis: fail`，队列消费停止。
3. MinIO/S3 不可用 → `/ready` 返回 503，`storage: fail`，产物无法交付。
4. ffmpeg 缺失 → `/ready` 返回 503，`media_tools: fail`，视频无法合并。
5. 下载目录不可写 → `/ready` 返回 503，`download_work_dir: fail`。

## 6. 权限边界

1. 本地临时路径 MUST NOT 出现在 API 响应、数据库或分享链接中。
2. MinIO/S3 预签名 URL 是唯一用户可访问的下载入口。
3. 临时文件生命周期由 runtime 管理，任务完成后清理。

## 7. 迁移/回滚影响

1. 本次变更仅涉及文档和 OpenSpec artifacts，无代码改动。
2. 代码改动由 PLAN15 子任务执行，有独立的迁移和回滚计划。
3. Dockerfile 和 Compose 的收敛是破坏性变更，需要一次性切换。
4. 如果需要回滚，恢复双 target Dockerfile 和双服务 Compose 即可。

## 8. 验证方式

1. PRD10 文档存在且内容完整。
2. DESIGN03 文档存在且内容完整。
3. ACC03 文档存在且内容完整。
4. 索引文件已更新。
5. OpenSpec artifacts 已创建。
6. `bash scripts/validate-repository.sh` 通过。
7. `git diff --check` 无问题。
