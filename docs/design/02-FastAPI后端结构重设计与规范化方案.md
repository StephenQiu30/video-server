---
layer: Design
doc_no: "02"
audience:
  - Dev
  - QA
  - Ops
feature_area: fastapi-backend-restructure
purpose: "定义万能视频下载器后端服务的 FastAPI 分层结构、模块边界、解析下载主链路规范化方案和后续实施内容。"
canonical_path: "docs/design/02-FastAPI后端结构重设计与规范化方案.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/design/01-个人自部署万能视频下载器技术设计.md"
  - "docs/prd/01-解析入口与URL安全.md"
  - "docs/prd/02-平台识别与平台画像.md"
  - "docs/prd/03-异步下载任务主链路.md"
  - "docs/prd/04-MinIO产物归档与下载交付.md"
  - "docs/prd/05-自部署运行与环境复用.md"
outputs:
  - "FastAPI 后端结构重设计方案"
  - "后端模块规范与迁移内容清单"
  - "解析下载与多分辨率能力完善边界"
triggers:
  - "调整后端目录结构、模块职责或依赖方向"
  - "完善解析、格式选择、下载执行、失败分类和归档主链路"
  - "引入新的 FastAPI 代码规范、测试门禁或 OpenAPI 契约约束"
downstream:
  - "docs/plans/05-Worker下载执行与失败分类计划.md"
  - "docs/plans/06-取消重试与事件流计划.md"
  - "docs/plans/07-MinIO对象归档计划.md"
  - "docs/plans/08-预签名下载与过期清理计划.md"
  - "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
---

# FastAPI 后端结构重设计与规范化方案

## 1. 背景

当前 `video-server` 已具备个人自部署万能视频下载器的后端主链路：FastAPI 接收解析和任务请求，Redis Queue 调度 Worker，Worker 调用 `yt-dlp` 下载并通过 FFmpeg 合并，最终把产物上传到 MinIO 并在 Postgres 中回写任务状态。

现阶段需要解决的问题不是重新证明项目方向，而是把后端服务结构按严格 FastAPI 工程规范重新梳理，使解析、格式选择、多分辨率下载、错误语义、任务状态、对象存储和测试门禁形成可长期维护的边界。后续实现应先以本文档为设计依据，再拆分计划和代码改造。

## 2. 目标

1. 定义后端 API、应用服务、领域模型、基础设施适配器和 Worker 的清晰分层，避免路由层、数据库层和第三方工具调用互相穿透。
2. 规范 `yt-dlp` 解析结果到内部格式选项的转换规则，确保多分辨率选择能被 Worker 稳定执行。
3. 固化任务状态、失败码、异常响应和日志脱敏规则，保证 API 与 Worker 对同一失败场景使用同一语义。
4. 给出渐进式迁移内容清单，保证重构期间不破坏现有 API 契约、OpenAPI 生成和自部署运行方式。
5. 明确测试门禁：后端核心行为必须由单元测试、API 契约测试和 Worker 适配器测试覆盖。

## 3. 非目标

- 不修改前端仓库，不设计前端页面、交互或状态映射。
- 不实现代码。本文件只定义后端结构、规范和后续需要做的内容。
- 不设计绕过 DRM、会员、付费墙、登录态限制或平台访问控制的能力。
- 不引入微服务拆分，不把 API、Worker、Storage 拆成多个独立部署仓库。
- 不把 AI 摘要、PDF 报告、字幕提取作为本轮结构优化主目标；它们只能作为下载成功后的增强产物模块接入。

## 4. 核心内容

### 4.1 后端目标分层

后端应采用单仓库、多运行时、分层模块结构：

```text
apps/api/app/
  api/
    routers/
    deps.py
    errors.py
  core/
    config.py
    logging.py
    security.py
  domain/
    tasks.py
    formats.py
    platforms.py
    failures.py
  schemas/
    parse.py
    tasks.py
    auth.py
    admin.py
    health.py
  services/
    parse_service.py
    task_service.py
    download_policy.py
    retention_service.py
  repositories/
    task_repository.py
    user_repository.py
    platform_repository.py
  infrastructure/
    ytdlp/
      parser.py
      selectors.py
      errors.py
    storage/
      object_storage.py
    queue/
      rq_queue.py
    media/
      ffmpeg_probe.py
  db/
    base.py
    session.py
    migrations.py

apps/worker/worker/
  jobs/
    download_job.py
    cleanup_job.py
  services/
    download_executor.py
    artifact_service.py
    enhanced_artifact_service.py
  infrastructure/
    ytdlp_downloader.py
    media_probe.py

packages/shared/video_downloader_shared/
  states.py
  error_codes.py
  constants.py
```

该结构是目标形态，不要求一次性移动所有文件。迁移时优先移动新增或正在修改的模块，避免为了目录整洁产生大规模无行为变化的改动。

### 4.2 依赖方向

依赖方向必须单向：

```text
api.routers -> schemas -> services -> repositories -> models/db
services -> domain
services -> infrastructure
worker.jobs -> worker.services -> domain/infrastructure
infrastructure -> third-party libraries
```

约束：

1. `routers` 只做协议转换、依赖注入和响应状态码，不直接拼装下载策略，不直接调用 `yt-dlp`。
2. `services` 负责编排业务流程，可以调用 repository 和 infrastructure，但不持有 FastAPI `Request` 或 `Response`。
3. `domain` 只放纯 Python 规则：状态机、格式选择、平台能力、失败码、配额判断，不依赖数据库会话和第三方 SDK。
4. `infrastructure` 封装 `yt-dlp`、Redis、MinIO、FFmpeg、外部 API 等易变依赖。
5. `worker` 只能通过 service/repository 边界修改任务状态，不直接复制 API 路由里的业务规则。

### 4.3 FastAPI 规范

API 层应遵循以下规范：

1. 每个 router 只负责一个资源边界：`parse`、`tasks`、`auth`、`admin`、`health`。
2. 所有响应模型必须使用 Pydantic schema，禁止直接暴露 SQLAlchemy model 的不稳定字段。
3. 所有业务错误统一转换为项目错误 envelope：

```json
{
  "success": false,
  "error": {
    "code": "invalid_url",
    "message": "请输入有效的视频链接",
    "details": null
  }
}
```

4. endpoint 函数保持薄层：参数校验、注入当前用户、调用 service、返回 schema。
5. OpenAPI 是前后端协作契约；后端修改 schema、状态枚举、错误码或端点路径时必须同步 `docs/openapi` 生成物和契约测试。
6. 鉴权、限流、数据库 session、当前用户解析必须放在统一 dependency 中，避免各 router 重复实现。

### 4.4 解析与多分辨率设计

解析服务目标是把第三方平台的 `yt-dlp` 原始结果转换成稳定的内部格式选项。

#### 4.4.1 内部格式模型

后端内部应区分三类格式：

| 类型 | 用途 | 示例 |
| --- | --- | --- |
| `recommended` | 自动选择最佳音视频并合并 | `bestvideo+bestaudio/best` |
| `preset` | 面向用户的分辨率预设 | `最高 1080p`、`最高 720p` |
| `raw` | 平台原始格式，主要用于调试和高级选择 | `30080 / 仅视频 / 1920x1080 / mp4` |

对外 schema 可继续使用 `VideoFormat`，但内部实现应使用领域对象承接转换，再由 schema adapter 输出。

#### 4.4.2 分辨率预设规则

解析服务应统一提供这些预设：

1. 推荐下载：总是可选。
2. 最高 1080p。
3. 最高 720p。
4. 最高 480p。
5. 最高 360p。

预设可用性由原始格式中可用视频流高度决定：

- 存在高度大于或等于目标高度的视频流时，预设可用。
- 不存在符合高度的视频流时，预设不可用，并给出中文 `note`。
- Worker 不做后端转码；所谓 720p/480p 表示选择来源中不超过目标高度的最佳可用流。

#### 4.4.3 format selector 规范

格式选择器必须由后端生成，用户提交任务时只能提交解析结果中出现过的 `format_id` 或受信任预设。

建议的 selector：

| 选项 | selector |
| --- | --- |
| 推荐下载 | `bestvideo+bestaudio/best` |
| 最高 1080p | `bv*[height<=1080]+ba/b[height<=1080]` |
| 最高 720p | `bv*[height<=720]+ba/b[height<=720]` |
| 最高 480p | `bv*[height<=480]+ba/b[height<=480]` |
| 最高 360p | `bv*[height<=360]+ba/b[height<=360]` |

任务创建接口不能信任前端传入的任意 selector。后续实现应在 `TaskCreate` 或 `TaskService.create_task` 中加入格式白名单策略：

1. 允许后端定义的预设 selector。
2. 允许本次解析结果返回的 raw `format_id`。
3. 拒绝超过长度限制、包含换行、shell 控制字符或不符合 `yt-dlp` selector 语法白名单的值。

### 4.5 下载任务服务设计

任务创建应由 `TaskService` 统一编排：

```text
normalize URL
-> validate public/safe URL
-> validate platform policy
-> validate selected format
-> assert user quota and concurrency
-> create download_tasks row
-> create queued event
-> enqueue worker job
-> return TaskRead
```

约束：

1. API 创建任务后只进入 `queued`，不得同步下载。
2. 任务创建成功但入队失败时，应回写 `failed`、`queue_unavailable` 和事件日志。
3. 重试任务必须复制原任务的 URL、标题、封面、时长、格式选择，并增加 `attempt_no`。
4. 取消只能作用于 `queued` 或 `running`，Worker 在下载进度 hook、上传前、上传后均需检查取消状态。

### 4.6 Worker 下载执行设计

Worker 应由 `DownloadJob` 调用 `DownloadExecutor` 完成执行：

```text
load task
-> skip terminal task
-> mark running
-> assert ffmpeg and ffprobe
-> run yt-dlp with task.format_id
-> resolve output file
-> assert file size
-> ffprobe media
-> upload artifact
-> mark succeeded
-> collect enhanced artifacts
-> cleanup workdir
```

`yt-dlp` 选项必须由专门 builder 生成，禁止散落在 job 函数中。选项必须包含：

1. `format`: 任务中的受信任 `format_id`。
2. `outtmpl`: 用户和任务隔离的工作目录。
3. `noplaylist`: 首版默认不下载播放列表。
4. `max_filesize`: 系统与用户配额中较小值。
5. `progress_hooks`: 进度回写与取消检查。
6. `ffmpeg_location`: 明确指向可用 FFmpeg。
7. `merge_output_format`: `mp4`。
8. Cookie 配置：优先 cookie file，其次 browser cookie，非法配置只记录 warning，不阻塞公开视频下载。

### 4.7 状态机与错误码

任务状态以 shared 枚举为唯一真相源：

| 状态 | 含义 |
| --- | --- |
| `queued` | 已创建，等待 Worker |
| `running` | Worker 正在下载、校验、上传或增强处理 |
| `succeeded` | 主视频已归档成功 |
| `failed` | 主视频下载、校验、上传或队列失败 |
| `canceled` | 用户取消任务 |

后端不得在 API 或测试中引入 `completed`、`success`、`downloading` 等状态别名。兼容旧前端显示逻辑可以留在前端，但后端契约必须保持单一枚举。

失败码分为 API 错误和 Worker 失败两类，但命名应统一放入 shared 常量：

| 错误码 | 场景 |
| --- | --- |
| `invalid_url` | URL 格式非法 |
| `unsafe_url` | 本机、内网、保留地址或风险地址 |
| `unsupported_platform` | 平台不支持或明显无法解析 |
| `platform_restricted` | 登录、会员、付费、DRM、地区或版权限制 |
| `platform_rate_limited` | 平台限流或风控 |
| `format_unavailable` | 所选清晰度或格式不可用 |
| `download_failed` | 下载内核失败，且无法归类到更具体错误 |
| `media_tools_missing` | FFmpeg 或 FFprobe 不可用 |
| `media_probe_failed` | 下载完成但媒体校验失败 |
| `storage_upload_failed` | 对象存储上传失败 |
| `queue_unavailable` | Redis Queue 不可用 |
| `task_timeout` | 任务运行超时 |
| `task_canceled` | Worker 感知到取消 |
| `retention_expired` | 产物已过期清理 |
| `rate_limited` | API 调用限流 |
| `limit_exceeded` | 用户配额或并发超限 |

### 4.8 URL 与平台安全规范

URL 进入解析或下载前必须完成标准化和安全校验：

1. 去除首尾空白。
2. 从分享文案中提取第一个 HTTP/HTTPS URL。
3. 缺少 scheme 时默认补 `https://`。
4. 拒绝非 HTTP/HTTPS scheme。
5. 拒绝 localhost、`.local`、`.localhost`、`.invalid`。
6. 拒绝 private、loopback、link-local、multicast、reserved、unspecified IP。
7. 首版不解析播放列表、频道、合集或批量 URL。

平台画像负责展示能力边界，不承诺所有 `yt-dlp` 支持站点都正式支持。未知公网 host 可以走 best-effort fallback，但错误语义必须稳定。

### 4.9 数据访问与事务规范

后续应逐步引入 repository 层，收束 SQLAlchemy 访问：

1. `TaskRepository`：创建任务、查询用户任务、查询任务事件、标记状态、清理过期产物。
2. `UserRepository`：用户查询、配额读取、管理员更新。
3. `PlatformRepository`：平台画像读取和后续数据库同步。

事务边界由 service 控制：

- 一个业务动作一个明确事务。
- Worker 长任务不得长时间持有未提交事务。
- 进度更新可以短事务提交，但必须避免高频提交压垮数据库。
- 任务状态与事件日志应在同一事务内写入。

### 4.10 配置与运行规范

配置继续由 Pydantic Settings 管理，但应分组沉淀：

1. `AppSettings`：环境、Host、Port、CORS。
2. `DatabaseSettings`：Postgres 连接和 bootstrap。
3. `QueueSettings`：Redis、RQ queue。
4. `DownloadSettings`：工作目录、文件大小、运行时长、并发。
5. `StorageSettings`：MinIO/S3。
6. `AuthSettings`：JWT、注册、GitHub OAuth。
7. `AISettings`：LLM、转写等增强能力。

实际代码可以继续保留单个 `Settings` 类，但字段命名、默认值和环境变量 alias 必须按这些分组维护。

### 4.11 日志与可观测性

后端日志必须满足：

1. 每个请求带 request id。
2. 下载任务日志带 `task_id`、`user_id`、`stage`。
3. 不记录完整 token、cookie、预签名 URL、密码、secret。
4. 平台错误保留可排查摘要，但不把外部异常原文完整返回给用户。
5. Worker 关键阶段写入 `task_events`，用于任务详情和验收排查。

### 4.12 测试门禁

后端结构优化必须保持或新增以下测试：

1. URL 标准化与安全拒绝测试。
2. 平台画像匹配测试。
3. 解析结果到 `VideoFormat` 的转换测试。
4. 分辨率预设可用性与 selector 测试。
5. 任务创建保存 `format_id`、`format_label`、状态和事件测试。
6. 任务状态筛选只接受 shared 枚举测试。
7. Worker `yt-dlp` options builder 测试。
8. Worker 失败分类测试。
9. MinIO 归档、预签名下载和过期清理测试。
10. OpenAPI 契约测试，保证 schema 变更被显式发现。

### 4.13 渐进迁移顺序

后续实施建议分 6 个阶段：

1. `shared` 规范化：统一状态枚举、失败码和 selector 常量。
2. 解析服务规范化：抽出 format domain、selector builder、parse adapter。
3. 任务服务规范化：引入 `TaskService` 和格式白名单校验。
4. Worker 规范化：抽出 options builder、download executor、artifact service。
5. Repository 收束：把任务、事件、用户和平台数据库访问移出 router/job。
6. 配置、日志和测试门禁收口：补齐 OpenAPI、pytest、健康检查和运行文档。

每个阶段都应保持 API 可运行、测试可通过，禁止一次性大规模移动文件导致行为难以审查。

## 5. 关联文档

### 5.1 输入文档

1. `docs/design/01-个人自部署万能视频下载器技术设计.md`
2. `docs/prd/01-解析入口与URL安全.md`
3. `docs/prd/02-平台识别与平台画像.md`
4. `docs/prd/03-异步下载任务主链路.md`
5. `docs/prd/04-MinIO产物归档与下载交付.md`
6. `docs/prd/05-自部署运行与环境复用.md`

### 5.2 输出文档

1. `docs/design/02-FastAPI后端结构重设计与规范化方案.md`

### 5.3 下游文档

1. `docs/plans/05-Worker下载执行与失败分类计划.md`
2. `docs/plans/06-取消重试与事件流计划.md`
3. `docs/plans/07-MinIO对象归档计划.md`
4. `docs/plans/08-预签名下载与过期清理计划.md`
5. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

## 6. 验收门禁

本文档完成后，应满足：

- 明确只覆盖 `video-server` 后端，不包含前端实施内容。
- 能解释当前 API、Worker、DB、Queue、Storage 的目标分层。
- 能指导后续代码重构，不需要开发者额外猜测模块职责。
- 覆盖解析、多分辨率选择、下载执行、失败分类、归档和测试门禁。
- 没有与 `docs/design/01-个人自部署万能视频下载器技术设计.md` 的状态机、对象存储和 API 边界冲突。

## 7. 风险与边界

1. 目录重构容易产生大量无行为变化 diff。实施时必须按阶段迁移，并用测试证明每阶段行为不变。
2. `yt-dlp` 平台适配受外部网站变化影响，后端只能稳定错误语义，不能承诺所有公网视频永久可解析。
3. 格式白名单需要在“安全限制”和“高级 raw 格式选择”之间平衡，首版应优先保证预设 selector 稳定。
4. Worker 下载和进度回写需要避免长事务和高频提交，否则可能影响 Postgres 性能。
5. Cookie 配置属于自部署增强能力，不能被设计成绕过付费、会员或访问控制的默认能力。

## 8. 待确认问题

1. 是否在下一阶段新增 `docs/plans/11-FastAPI后端结构规范化实施计划.md`，把本文档拆成可执行任务。
2. 是否保留 raw format 对普通任务创建开放，或只允许推荐与分辨率预设。
3. 是否把 `platform_profiles` 长期保留为代码配置，还是在后续阶段同步为数据库表。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-16 | StephenQiu30 | 0.1.0 | 初始化 FastAPI 后端结构重设计与规范化方案 |
