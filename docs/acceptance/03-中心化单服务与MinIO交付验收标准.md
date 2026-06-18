---
layer: Acceptance
doc_no: "03"
audience:
  - Dev
  - QA
  - Ops
feature_area: centralized-single-service-minio-delivery
purpose: "定义中心化单服务运行时和 MinIO 交付的验收标准，覆盖单服务架构、端到端链路、本地路径隔离和 readiness 规则。"
canonical_path: "docs/acceptance/03-中心化单服务与MinIO交付验收标准.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/10-中心化单服务运行时.md"
  - "docs/design/03-中心化单服务架构重评审.md"
outputs:
  - "中心化单服务验收标准"
  - "MinIO 交付验收标准"
  - "端到端链路验收场景"
triggers:
  - "验收中心化单服务运行时实现"
  - "验证 MinIO 交付边界"
  - "验证本地路径隔离"
downstream:
  - "PLAN15 子任务"
---

# ACC03 中心化单服务与 MinIO 交付验收标准

## 1. 概述

本文档定义 PRD10 和 DESIGN03 的验收标准。验收必须证明：单服务架构可行、端到端链路可完成、本地路径不泄漏、readiness 覆盖全部组件。

## 2. 单服务架构验收

### 2.1 Compose 单服务

| 验收项 | 验收标准 | 验证方式 |
| --- | --- | --- |
| 业务服务数量 | Compose 中只有一个业务服务 `app` | 检查 `docker-compose.yml` |
| Docker target | `app` 服务使用单个 Docker target | 检查 `Dockerfile` |
| 容器名 | 容器名为 `stephen-video-app` | 检查 `docker-compose.yml` |
| 基础设施独立 | PostgreSQL、Redis、MinIO 保持独立容器 | 检查 `docker-compose.yml` |

### 2.2 代码单入口

| 验收项 | 验收标准 | 验证方式 |
| --- | --- | --- |
| 部署入口 | 代码层只有一个部署入口 `app.runtime` | 检查 `app/runtime.py` |
| API 启动 | `app.runtime` 内部启动 FastAPI server | 代码审查 |
| Worker 启动 | `app.runtime` 内部启动 RQ Worker 循环 | 代码审查 |
| 旧入口废弃 | `apps/worker/worker/main.py` 不再作为独立入口 | 代码审查 |

### 2.3 队列内部化

| 验收项 | 验收标准 | 验证方式 |
| --- | --- | --- |
| Redis 保留 | Redis 仍作为消息队列基础设施 | 检查 Compose 和代码 |
| RQ 保留 | RQ 仍作为任务队列机制 | 检查代码 |
| 内部消费 | 队列消费在 `app` 容器内部运行 | 检查 `app/runtime.py` |
| 非同步执行 | API 不同步执行长耗时下载 | 代码审查 |

## 3. 端到端链路验收

### 3.1 完整链路

```gherkin
Scenario: 分享视频链接完成端到端链路
  Given 系统已启动且所有组件就绪
  When 用户通过 /api/parse 解析一个公开视频 URL
  Then 系统返回可下载 format 列表
  When 用户通过 /api/tasks 创建下载任务
  Then 系统返回任务 ID 和 pending 状态
  When RQ Worker 消费该任务
  Then Worker 执行 yt-dlp 下载和 FFmpeg 合并
  And 产物上传到 MinIO/S3
  And 任务状态更新为 completed
  And 任务记录包含 presigned_url
  When 用户通过 presigned_url 下载
  Then 返回视频文件
```

### 3.2 链路验证命令

```bash
# 1. 启动系统
npm run docker:up

# 2. 检查健康
curl http://localhost:8000/health
# 期望: {"status":"ok","app":"video-server"}

# 3. 检查就绪
curl http://localhost:8000/ready
# 期望: {"status":"ready","checks":{...}}

# 4. 解析视频
curl -X POST http://localhost:8000/api/parse \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.bilibili.com/video/BV1xx411c7mD"}'

# 5. 创建任务
curl -X POST http://localhost:8000/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"url":"https://www.bilibili.com/video/BV1xx411c7mD","format_id":"..."}'

# 6. 查询任务状态
curl http://localhost:8000/api/tasks/{task_id}

# 7. 通过 presigned_url 下载
curl -L "{presigned_url}" -o video.mp4
```

## 4. 本地路径隔离验收

### 4.1 路径泄漏检查

| 验收项 | 验收标准 | 验证方式 |
| --- | --- | --- |
| API 响应 | `/api/tasks` 响应不包含本地路径 | 检查响应 JSON |
| 数据库 | `tasks` 表不存储本地路径 | 检查数据库记录 |
| 分享链接 | presigned_url 不包含本地路径 | 检查 URL 格式 |
| 临时文件 | 下载临时文件在容器内部 `/tmp/` | 检查容器文件系统 |

### 4.2 路径泄漏验证命令

```bash
# 检查 API 响应不包含本地路径
curl http://localhost:8000/api/tasks/{task_id} | grep -v "/tmp/"
curl http://localhost:8000/api/tasks/{task_id} | grep -v "/app/"

# 检查数据库不存储本地路径
docker exec stephen-video-postgres psql -U postgres -d video_server \
  -c "SELECT * FROM tasks WHERE id = '{task_id}'" | grep -v "/tmp/"
```

## 5. Readiness 验收

### 5.1 全部就绪

```gherkin
Scenario: 所有组件就绪
  Given PostgreSQL、Redis、MinIO 和 ffmpeg 均可用
  When 请求 GET /ready
  Then 返回 HTTP 200
  And 响应包含 status: "ready"
  And 所有 checks 为 "ok"
```

### 5.2 组件不可用

```gherkin
Scenario: Redis 不可用
  Given PostgreSQL 可用但 Redis 不可用
  When 请求 GET /ready
  Then 返回 HTTP 503
  And 响应包含 status: "not_ready"
  And checks.redis 为 "fail"
  And checks.queue 为 "fail"
  And 其他 checks 为 "ok"
```

### 5.3 Readiness 验证命令

```bash
# 全部就绪
curl -s http://localhost:8000/ready | jq .
# 期望: {"status":"ready","checks":{"db":"ok","redis":"ok",...}}

# 停止 Redis 后检查
docker stop stephen-video-redis
curl -s http://localhost:8000/ready | jq .
# 期望: {"status":"not_ready","checks":{"db":"ok","redis":"fail","queue":"fail",...}}

# 恢复 Redis
docker start stephen-video-redis
```

## 6. Agent Review 关注点

1. 检查文档是否仍把 API/Worker 表达为两个业务服务。
2. 检查文档是否误把本地路径作为交付方式。
3. 检查 PRD10、DESIGN03、ACC03 对单服务、MinIO 交付和本地路径隔离的描述一致。
4. 检查 readiness 规则是否覆盖全部组件。

## 7. 验证方式

### 7.1 自动化

```bash
bash scripts/validate-repository.sh
git diff --check
```

### 7.2 手动

1. 复核 PRD10、DESIGN03、ACC03 对单服务、MinIO 交付和本地路径隔离的描述一致。
2. 复核文档中不再把 API/Worker 表达为两个业务服务。
3. 复核 readiness 规则覆盖全部组件。

### 7.3 残余风险

1. 单容器运行 API 和 Worker 意味着资源隔离减少。
2. Worker 线程异常可能影响 API（需要容器重启恢复）。
3. Dockerfile 和 Compose 的收敛是破坏性变更。
