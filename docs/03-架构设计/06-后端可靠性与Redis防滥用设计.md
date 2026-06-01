---
layer: Design
doc_no: "06"
audience:
  - Dev
  - QA
  - Ops
feature_area: backend-reliability
purpose: "定义 Worker 类型化流水线、任务可靠性边界、Redis 接口限流、登录注册锁、全局异常处理与统一接口响应封装的后端工程化设计。"
canonical_path: "docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/03-架构设计/05-后端上线级工程化升级设计.md"
  - "docs/04-执行计划/05-后端上线级工程化任务拆分.md"
outputs:
  - "Worker 类型化流水线设计"
  - "Redis 限流与登录注册锁设计"
  - "全局异常处理与统一接口响应封装设计"
triggers:
  - "下载任务可靠性不足"
  - "需要支持多实例上线防滥用"
  - "Worker 文件职责膨胀需要拆分"
  - "接口错误响应缺少统一契约"
downstream:
  - "docs/04-执行计划/06-后端可靠性与Redis防滥用任务拆分.md"
  - "docs/05-测试验收/03-上线级SaaS验收标准.md"
---

# 后端可靠性与 Redis 防滥用设计

## 1. 背景

当前后端已经具备账号体系、下载任务、对象存储、平台解析、生产配置门禁、请求 ID、安全响应头和基础解析限流。下一阶段主要风险集中在两个方向：

1. Worker 下载链路仍由 `apps/worker/worker/jobs.py` 集中承担下载、媒体校验、上传、AI 后处理、失败分类和清理职责，文件职责过宽。
2. 接口防滥用仍以进程内限流为主，多实例部署时 `/api/parse`、`/api/tasks`、登录、注册等入口缺少 Redis 级共享保护。

因此本设计将 Worker 可靠性、Redis 防滥用和 API 合同治理作为同一阶段的后端工程化主题，但在实现上保持清晰边界：Worker 流水线负责任务执行可信，Redis 限流/锁负责入口流量可信，全局异常与统一响应封装负责接口契约可信。

## 2. 目标

- 使用 Enum 和 DTO 固化 Worker 阶段、失败码、下载产物、存储产物和 AI 后处理结果。
- 将 Worker 主入口收缩为编排层，下载、媒体校验、上传、AI、失败分类分别由独立模块承担。
- 增加任务幂等边界，避免成功任务、取消任务和重复入队任务被重复处理。
- 使用 Redis 实现多实例共享的接口限流和登录注册锁。
- 统一处理 `AppError`、`HTTPException`、请求参数校验异常和未知异常。
- 统一失败响应结构，避免错误返回在不同接口之间不一致。
- 保留 local/testing 的内存 fallback，避免本机调试强依赖 Redis。
- 所有行为变更按 TDD 红绿流程执行，保持 API 成功响应兼容。

## 3. 非目标

- 不替换 RQ，不引入 Celery、Kafka 或新的任务系统。
- 不引入 Kubernetes、OpenTelemetry、Prometheus 服务端或复杂网关。
- 不做前端改造。
- 不改变 `/api/tasks` 和 `/api/parse` 的成功响应结构。
- 不在本阶段强制把全部成功响应迁移为 envelope，成功响应统一封装需要和前端单独协同。
- 不把真实平台 smoke 测试纳入默认 CI。
- 不在本阶段引入 Alembic；数据库迁移治理保留为后续 P2。

## 4. 核心设计

### 4.1 Worker Domain 枚举

新增 `apps/worker/worker/domain.py`，集中定义 Worker 内部类型，不放业务副作用。

建议枚举：

```python
from enum import StrEnum


class WorkerStage(StrEnum):
    START = "start"
    DOWNLOAD = "download"
    PROBE = "probe"
    UPLOAD = "upload"
    AI = "ai"
    CLEANUP = "cleanup"


class WorkerFailureCode(StrEnum):
    DOWNLOAD_FAILED = "download_failed"
    FORMAT_UNAVAILABLE = "format_unavailable"
    FILE_TOO_LARGE = "file_too_large"
    MEDIA_TOOLS_MISSING = "media_tools_missing"
    FFPROBE_FAILED = "ffprobe_failed"
    STORAGE_FAILED = "storage_failed"
    TASK_TIMEOUT = "task_timeout"
    TASK_CANCELED = "task_canceled"
    PLATFORM_RESTRICTED = "platform_restricted"
    PLATFORM_RATE_LIMITED = "platform_rate_limited"
    UNSUPPORTED_PLATFORM = "unsupported_platform"
    BROWSER_COOKIES_UNAVAILABLE = "browser_cookies_unavailable"


class AIProcessStatus(StrEnum):
    SKIPPED = "skipped"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
```

`TaskState` 继续使用 `packages/shared/video_downloader_shared/states.py` 中已有定义，不重复创建任务状态枚举。

### 4.2 Worker DTO

建议 DTO：

```python
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(frozen=True)
class WorkerContext:
    task_id: str
    user_id: int
    source_url: str
    format_id: str
    title: str
    work_dir: Path
    max_file_size_bytes: int
    file_retention_hours: int


@dataclass(frozen=True)
class DownloadArtifact:
    path: Path
    filename: str
    size_bytes: int
    content_type: str = "application/octet-stream"


@dataclass(frozen=True)
class StoredArtifact:
    object_key: str
    object_size: int
    expires_at: datetime


@dataclass(frozen=True)
class FailureInfo:
    code: WorkerFailureCode
    reason: str
    stage: WorkerStage
    retryable: bool


@dataclass(frozen=True)
class AIProcessResult:
    status: AIProcessStatus
    summary: str | None = None
    mindmap: str | None = None
    error: str | None = None
```

这些 DTO 用于内部边界，不直接暴露给前端。

### 4.3 Worker 模块拆分

建议模块边界：

| 模块 | 职责 | 输入 | 输出 |
| --- | --- | --- | --- |
| `worker/domain.py` | Enum 与 DTO | 无 | 类型定义 |
| `worker/failures.py` | 异常到 `FailureInfo` 的转换 | `Exception`, `WorkerStage` | `FailureInfo` |
| `worker/download_runner.py` | yt-dlp 下载、进度 hook、输出路径解析 | `WorkerContext`, SQLAlchemy session task handle | `DownloadArtifact` |
| `worker/media_probe.py` | ffmpeg/ffprobe 检查和媒体校验 | `DownloadArtifact` | 无副作用校验结果 |
| `worker/artifact_storage.py` | 上传、对象 key、取消后对象清理 | `WorkerContext`, `DownloadArtifact` | `StoredArtifact` |
| `worker/ai_pipeline.py` | 音频抽取、转录、总结、思维导图 | `DownloadArtifact` | `AIProcessResult` |
| `worker/jobs.py` | RQ 入口和流程编排 | `task_id` | DB 状态与事件 |

`jobs.py` 只保留状态流转、取消检查、模块调用和最终 DB 写入，不再承载每个阶段的细节实现。

### 4.4 任务幂等边界

Worker 入口必须先判断任务状态：

- 任务不存在：直接返回。
- `canceled`：直接返回，不下载。
- `succeeded` 且 `object_key` 存在：记录或静默跳过，不重复上传。
- `running` 且更新时间未超时：避免重复执行。
- 已失败任务的重试应通过现有 retry 机制创建新任务，不在同一任务上反复覆盖历史。

上传后的取消边界：

- 上传完成后再次检查取消状态。
- 如果任务已取消，删除刚上传对象，记录取消事件，不把任务改成成功。

AI 后处理边界：

- 主下载成功后才进入 AI。
- AI 失败只写入 `ai_status=failed` 和 `ai_error`，不回滚主任务 `succeeded`。

### 4.5 Redis 接口限流

新增或扩展 `apps/api/app/services/rate_limit.py`：

```python
from dataclasses import dataclass
from enum import StrEnum


class RateLimitScope(StrEnum):
    PARSE = "parse"
    CREATE_TASK = "create_task"
    LOGIN = "login"
    REGISTER = "register"


@dataclass(frozen=True)
class RateLimitPolicy:
    scope: RateLimitScope
    limit: int
    window_seconds: int
    lock_seconds: int | None = None


@dataclass(frozen=True)
class RateLimitResult:
    allowed: bool
    remaining: int
    retry_after_seconds: int | None
```

实现策略：

- `RedisRateLimiter` 使用 Redis key + TTL 计数。
- `InMemoryRateLimiter` 保留为 local/testing fallback。
- 生产环境默认使用 Redis；Redis 不可用时默认 fail-open 并记录告警，避免 Redis 短抖导致全站不可用。
- 关键 key 统一命名：`video:ratelimit:{scope}:{identity}`。

建议默认策略：

| 接口 | Scope | 身份维度 | 默认策略 |
| --- | --- | --- | --- |
| `/api/parse` | `parse` | user id | 60 次 / 分钟 |
| `/api/tasks` | `create_task` | user id | 20 次 / 分钟 |
| 登录 | `login` | email hash + IP | 失败 5 次锁 15 分钟 |
| 注册 | `register` | IP | 10 次 / 小时 |

### 4.6 登录注册锁

登录注册锁与普通限流不同：普通限流按请求次数拒绝，登录锁主要按失败次数拒绝。

建议新增 `apps/api/app/services/auth_lock.py`：

```python
from enum import StrEnum


class AuthLockScope(StrEnum):
    LOGIN_EMAIL = "login_email"
    LOGIN_IP = "login_ip"
    REGISTER_IP = "register_ip"
```

行为边界：

- 登录失败后累计 email hash 和 IP 两类计数。
- 登录成功后清除 email hash 锁计数。
- 注册按 IP 限制，不按 email 锁死，避免攻击者用目标邮箱恶意锁账号。
- 错误使用 `AppError("auth_locked", "...", 429)`。

### 4.7 全局异常处理

当前工程已经有 `AppError` 和部分异常处理能力，但上线级接口需要把错误响应视为稳定契约。建议在 `apps/api/app/core/errors.py` 与 `apps/api/app/core/responses.py` 中集中定义异常与响应结构，并在 FastAPI app 启动处统一注册 handlers。

统一失败响应：

```json
{
  "success": false,
  "error": {
    "code": "rate_limited",
    "message": "请求过于频繁，请稍后再试",
    "details": null
  }
}
```

建议异常映射：

| 异常类型 | HTTP 状态 | `error.code` | 用户可见文案 |
| --- | --- | --- | --- |
| `AppError` | 异常自带 | 异常自带 | 异常自带 |
| `HTTPException(401)` | 401 | `unauthorized` | `请先登录后再继续操作` |
| `HTTPException(403)` | 403 | `forbidden` | `当前账号没有权限执行该操作` |
| `HTTPException(404)` | 404 | `not_found` | `资源不存在` |
| `RequestValidationError` | 422 | `validation_error` | `请求参数不符合要求` |
| 未知异常 | 500 | `internal_error` | `服务暂时不可用，请稍后重试` |

未知异常处理要求：

- 记录 `request_id`、path、method 和异常堆栈。
- 响应中不返回堆栈、数据库错误、对象存储 key、Redis key、Cookie 或 token。
- local/testing 可以保留更完整日志，但接口返回仍保持统一结构。

### 4.8 统一响应封装边界

本阶段建议先统一失败响应，成功响应保持兼容，原因是当前前端和测试已经依赖多个接口的成功响应模型。如果一次性把成功响应改为 `{ "success": true, "data": ... }`，会扩大前后端联调范围，并且不符合当前“先优化后端服务”的边界。

分阶段策略：

1. P1：统一失败响应 envelope，保持成功响应结构不变。
2. P2：在前端仓库同步 API client 后，再评估成功响应是否统一为 `{ "success": true, "code": "ok", "message": "ok", "data": ... }`。

对本轮 Redis 限流和登录注册锁的要求：

- 限流返回 `429` + `error.code=rate_limited`。
- 登录注册锁返回 `429` + `error.code=auth_locked`。
- 请求参数错误返回 `422` + `error.code=validation_error`。
- 鉴权失败返回 `401` + `error.code=unauthorized`。

## 5. 关联文档

### 5.1 输入文档

1. `docs/03-架构设计/05-后端上线级工程化升级设计.md`
2. `docs/04-执行计划/05-后端上线级工程化任务拆分.md`
3. `CLAUDE.md`

### 5.2 输出文档

1. `docs/04-执行计划/06-后端可靠性与Redis防滥用任务拆分.md`

### 5.3 下游文档

1. `docs/05-测试验收/03-上线级SaaS验收标准.md`
2. `docs/06-运维合规/02-风险与合规边界.md`

## 6. 验收门禁

- `apps/worker/worker/jobs.py` 收缩为编排层，单文件职责明显减少。
- Worker 新增 Enum/DTO 的单元测试。
- 幂等、取消、上传失败、AI 失败均有测试覆盖。
- `/api/parse`、`/api/tasks`、登录、注册限流或锁定行为有测试覆盖。
- `AppError`、`HTTPException`、请求校验异常和未知异常均有统一失败响应测试覆盖。
- Redis 不可用 fallback 行为有测试覆盖。
- `npm test` 通过。
- CI 通过。

## 7. 风险与边界

- Redis fail-open 会降低防滥用强度，但能避免 Redis 抖动导致核心业务全部不可用；后续可通过配置切换 fail-closed。
- Worker 拆分应保持行为等价，不能借机扩大下载平台能力或改变 API 响应。
- AI 后处理仍依赖外部模型服务，必须继续作为可失败的附属流程，而不是主下载成功的前置条件。
- 登录注册锁需要避免泄露账号存在性，错误文案应保持泛化。
- 成功响应 envelope 不在本阶段执行，避免破坏当前前端和已有测试依赖的成功响应模型。

## 8. 待确认问题

- 生产环境 Redis 限流故障时是否保持默认 fail-open。
- 登录锁是否需要同时按 email hash 和 IP 双维度执行。
- `/api/tasks` 创建任务限流默认值是否采用 20 次 / 分钟。
- 本阶段是否确认只统一失败响应，成功响应 envelope 留到前端 API client 协同阶段。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-05-23 | StephenQiu30 | 0.1.0 | 初始化 Worker 类型化流水线、Redis 防滥用、全局异常与统一失败响应设计 |
