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
version: "0.2.0"
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
  - "视频源接入设计模式与扩展规范"
  - "全局响应格式与异常处理规范"
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
    source_adapters.py
    failures.py
  schemas/
    parse.py
    tasks.py
    auth.py
    admin.py
    health.py
  services/
    parse_service.py
    source_registry.py
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
      source_clients.py
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

### 4.5 视频源接入设计模式

视频源接入是后端长期扩展点，必须用明确的软件设计模式约束，避免每新增一个平台都在 `parse_service`、`download_executor` 或 router 中堆条件判断。

#### 4.5.1 设计目标

1. 新增视频源时只新增 adapter、profile 和测试，不改动主流程。
2. 解析、格式转换、下载策略和错误映射可以按平台定制。
3. 平台差异被封装在 adapter 内，API、任务服务和 Worker 只依赖统一接口。
4. 支持从“通用 yt-dlp fallback”逐步升级为“平台专用 adapter”。

#### 4.5.2 核心模式

| 模式 | 用途 | 在本项目中的落点 |
| --- | --- | --- |
| Adapter | 把平台或 `yt-dlp` 原始能力适配为内部统一接口 | `VideoSourceAdapter` |
| Strategy | 按平台选择解析策略、格式策略和错误映射策略 | `ParseStrategy`、`FormatStrategy`、`ErrorMappingStrategy` |
| Registry | 管理所有已注册视频源 adapter | `VideoSourceRegistry` |
| Factory | 根据 URL、平台画像或 extractor 创建合适 adapter | `VideoSourceAdapterFactory` |
| Template Method | 固定解析主流程，把平台差异留给 hook | `BaseVideoSourceAdapter.parse()` |
| Value Object | 表达 URL、平台、格式、selector 等不可变领域值 | `SourceUrl`、`VideoFormatOption`、`FormatSelector` |

#### 4.5.3 统一 adapter 接口

所有视频源 adapter 必须实现同一协议：

```python
class VideoSourceAdapter(Protocol):
    source_id: str
    display_name: str

    def supports(self, source_url: SourceUrl) -> bool:
        ...

    def parse(self, source_url: SourceUrl) -> ParsedVideo:
        ...

    def build_download_options(
        self,
        task: DownloadTaskSpec,
        format_selector: FormatSelector,
    ) -> DownloadOptions:
        ...

    def map_error(self, exc: Exception) -> FailureInfo:
        ...
```

约束：

1. `supports()` 只能做轻量判断，不能访问外部网络。
2. `parse()` 可以调用 `yt-dlp` 或平台专用解析器，但必须返回内部 `ParsedVideo`。
3. `build_download_options()` 只能生成下载参数，不执行下载。
4. `map_error()` 必须把外部异常转换为 shared failure code。
5. adapter 不能直接写数据库，不能直接创建任务，不能返回 FastAPI response。

#### 4.5.4 Registry 与 Factory

`VideoSourceRegistry` 负责注册和检索 adapter：

```text
register(BilibiliAdapter)
register(DouyinAdapter)
register(YouTubeAdapter)
register(GenericYtDlpAdapter)

resolve(source_url)
-> first adapter where supports(source_url) is True
-> fallback GenericYtDlpAdapter
```

注册顺序必须从专用到通用：

1. 国内短视频专用 adapter。
2. Bilibili 专用 adapter。
3. YouTube/TikTok 等公开平台 adapter。
4. `GenericYtDlpAdapter` fallback。

Factory 负责把 URL、平台画像、配置开关组合起来，返回可用 adapter。Factory 可以读取配置，但不能执行解析或下载。

#### 4.5.5 平台接入文件结构

新增视频源应按以下结构进入项目：

```text
apps/api/app/infrastructure/sources/
  base.py
  registry.py
  generic_ytdlp.py
  bilibili.py
  douyin.py
  youtube.py

apps/api/app/domain/
  source_url.py
  source_profile.py
  parsed_video.py
  format_selector.py

apps/api/tests/sources/
  test_registry.py
  test_bilibili_adapter.py
  test_douyin_adapter.py
  test_generic_ytdlp_adapter.py
```

Worker 侧下载执行可以复用同一套 selector 和 error mapping，但不要直接依赖 API router。共享规则应放入 `packages/shared` 或 API/Worker 都能引用的 domain 模块。

#### 4.5.6 新视频源接入流程

接入一个新视频源必须按以下顺序：

1. 新增或更新平台画像：`platform_id`、`display_name`、host 列表、合规说明、能力标记。
2. 新增 adapter：实现 `supports()`、`parse()`、错误映射和可选下载参数策略。
3. 注册 adapter：加入 registry，顺序必须在 fallback 之前。
4. 新增解析测试：覆盖 URL 匹配、解析字段、格式转换、合规提示。
5. 新增失败测试：覆盖登录限制、格式不可用、平台限流、网络超时。
6. 新增 OpenAPI 契约测试：确保对外 schema 不因平台差异漂移。
7. 更新设计或运维文档：记录平台边界和已知限制。

验收标准：

- 新增平台不需要修改 `parse` router。
- 新增平台不需要修改任务创建主流程。
- 新增平台不需要在 Worker job 中增加平台条件分支。
- 所有平台错误都能落到统一 `failure_code`。

### 4.6 全局响应格式与异常处理

后端必须定义全局响应 envelope 和全局异常映射。目标是让 API、测试、OpenAPI 和运维日志对成功和失败有同一套语言。

#### 4.6.1 成功响应格式

业务 API 成功响应统一采用以下概念模型：

```json
{
  "success": true,
  "data": {},
  "meta": {
    "request_id": "req_...",
    "timestamp": "2026-06-16T12:00:00Z"
  }
}
```

考虑到现有 API 已直接返回 `TaskRead`、`ParseResponse` 等 schema，迁移策略为：

1. 新增 API 或管理类 API 优先采用 envelope。
2. 既有用户主链路 API 在一个兼容阶段内可以保持当前响应体，避免破坏 OpenAPI 和调用方。
3. 如果决定全量 envelope 化，必须先更新 OpenAPI、契约测试和前后端协作文档。

无论响应体是否 envelope 化，所有请求都必须具备可追踪的 `request_id`。

#### 4.6.2 分页响应格式

列表类 API 应使用统一分页结构：

```json
{
  "success": true,
  "data": {
    "items": [],
    "page": 1,
    "page_size": 20,
    "total": 0
  },
  "meta": {
    "request_id": "req_..."
  }
}
```

`GET /api/tasks` 当前支持 `limit`，后续如需要分页，应迁移到 `page/page_size` 或 cursor 模式，并在 design/plan 中显式说明兼容策略。

#### 4.6.3 错误响应格式

所有异常响应必须使用统一 failure envelope：

```json
{
  "success": false,
  "error": {
    "code": "format_unavailable",
    "message": "该视频源未提供所选清晰度，请选择推荐下载或其他可用清晰度后重试。",
    "details": null
  },
  "meta": {
    "request_id": "req_..."
  }
}
```

约束：

1. `code` 使用 shared error code，不允许自由字符串散落在代码中。
2. `message` 面向用户，可中文展示，不包含 token、cookie、secret、完整预签名 URL 或外部异常堆栈。
3. `details` 只放可安全暴露的结构化信息，默认 `null`。
4. 5xx 错误不能把内部异常原文返回给用户。
5. 日志可以记录内部异常摘要和 traceback，但必须做敏感信息脱敏。

#### 4.6.4 全局异常映射

FastAPI 应集中注册 exception handlers：

| 异常类型 | HTTP 状态码 | 错误码 |
| --- | --- | --- |
| `AppError` | 使用异常自带状态码 | 使用异常自带 code |
| `RequestValidationError` | 422 | `validation_error` |
| `AuthenticationError` | 401 | `unauthorized` |
| `AuthorizationError` | 403 | `forbidden` |
| `RateLimitError` | 429 | `rate_limited` |
| `SQLAlchemyError` | 500 | `database_error` |
| `RedisError` | 503 | `queue_unavailable` |
| `BotoCoreError` / S3 client error | 503 | `storage_unavailable` 或 `storage_upload_failed` |
| `yt-dlp` 解析异常 | 422/503 | `platform_restricted`、`platform_rate_limited`、`platform_unavailable` |
| 未捕获异常 | 500 | `internal_error` |

异常处理器职责：

1. 生成统一 failure envelope。
2. 注入 `request_id`。
3. 记录结构化日志。
4. 对外隐藏内部异常细节。
5. 保持 OpenAPI 中错误模型可追踪。

#### 4.6.5 领域异常层次

项目应逐步从单个 `AppError` 扩展为可维护的领域异常层次：

```text
AppError
  ValidationAppError
  AuthAppError
  PermissionAppError
  RateLimitAppError
  QuotaExceededError
  UnsupportedPlatformError
  FormatUnavailableError
  DownloadExecutionError
  StorageAppError
  QueueAppError
```

领域异常可以继承统一基类，但每个异常必须显式声明：

- `code`
- `message`
- `status_code`
- `safe_details`
- `log_level`

### 4.7 软件工程约束

本项目后端后续改造必须使用软件工程范式约束，而不是只追求“能跑”。

#### 4.7.1 SOLID 约束

1. 单一职责：router、service、repository、adapter、schema 各自只承担一种原因的变化。
2. 开闭原则：新增视频源通过新增 adapter 和注册完成，不修改解析主流程。
3. 里氏替换：所有 `VideoSourceAdapter` 必须能被 registry 以同一方式调用。
4. 接口隔离：解析、下载、错误映射不强迫所有 adapter 实现无关能力。
5. 依赖倒置：业务服务依赖抽象协议，不直接依赖 `yt-dlp`、Redis、MinIO 具体 SDK。

#### 4.7.2 分层架构约束

1. 禁止 router 直接访问 `yt-dlp`、MinIO、Redis SDK。
2. 禁止 infrastructure 反向依赖 service 或 router。
3. 禁止 domain 依赖 FastAPI、SQLAlchemy session 或外部 SDK。
4. repository 返回领域对象或 ORM model 的边界必须明确，不得把查询细节泄漏到 router。
5. Worker job 只能作为异步入口，不承载复杂业务规则。

#### 4.7.3 契约优先

1. Pydantic schema 是 API 入参和出参契约。
2. shared 枚举是状态、错误码和 selector 常量的真相源。
3. OpenAPI 变更必须由测试发现，并同步文档。
4. 任何破坏兼容的响应格式变化都必须先有 design/plan，再进入实现。

#### 4.7.4 测试优先

涉及行为变化时必须按 Red -> Green -> Refactor：

1. 先写失败测试描述目标行为。
2. 再写最小实现通过测试。
3. 最后在测试保护下移动目录或抽象接口。

设计模式相关测试至少包括：

- registry 选择正确 adapter。
- fallback adapter 在未知公网 host 上生效。
- adapter 错误映射到统一 failure code。
- 新增平台不需要改 router 的契约测试。
- 全局异常 handler 对 AppError、validation error、unknown error 输出统一 envelope。

#### 4.7.5 复杂度控制

1. 单个 Python 文件长期目标不超过 200 行；超过时按职责拆分。
2. 单个函数优先控制在 40 行以内；复杂流程使用 service 编排和小函数表达。
3. 禁止通过全局变量保存请求态、用户态或任务态。
4. 禁止把平台特殊逻辑写成多层 `if platform_id == ...`。
5. 所有外部依赖都必须被封装到 infrastructure，便于测试替换。

### 4.8 下载任务服务设计

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

### 4.9 Worker 下载执行设计

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

### 4.10 状态机与错误码

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

### 4.11 URL 与平台安全规范

URL 进入解析或下载前必须完成标准化和安全校验：

1. 去除首尾空白。
2. 从分享文案中提取第一个 HTTP/HTTPS URL。
3. 缺少 scheme 时默认补 `https://`。
4. 拒绝非 HTTP/HTTPS scheme。
5. 拒绝 localhost、`.local`、`.localhost`、`.invalid`。
6. 拒绝 private、loopback、link-local、multicast、reserved、unspecified IP。
7. 首版不解析播放列表、频道、合集或批量 URL。

平台画像负责展示能力边界，不承诺所有 `yt-dlp` 支持站点都正式支持。未知公网 host 可以走 best-effort fallback，但错误语义必须稳定。

### 4.12 数据访问与事务规范

后续应逐步引入 repository 层，收束 SQLAlchemy 访问：

1. `TaskRepository`：创建任务、查询用户任务、查询任务事件、标记状态、清理过期产物。
2. `UserRepository`：用户查询、配额读取、管理员更新。
3. `PlatformRepository`：平台画像读取和后续数据库同步。

事务边界由 service 控制：

- 一个业务动作一个明确事务。
- Worker 长任务不得长时间持有未提交事务。
- 进度更新可以短事务提交，但必须避免高频提交压垮数据库。
- 任务状态与事件日志应在同一事务内写入。

### 4.13 配置与运行规范

配置继续由 Pydantic Settings 管理，但应分组沉淀：

1. `AppSettings`：环境、Host、Port、CORS。
2. `DatabaseSettings`：Postgres 连接和 bootstrap。
3. `QueueSettings`：Redis、RQ queue。
4. `DownloadSettings`：工作目录、文件大小、运行时长、并发。
5. `StorageSettings`：MinIO/S3。
6. `AuthSettings`：JWT、注册、GitHub OAuth。
7. `AISettings`：LLM、转写等增强能力。

实际代码可以继续保留单个 `Settings` 类，但字段命名、默认值和环境变量 alias 必须按这些分组维护。

### 4.14 日志与可观测性

后端日志必须满足：

1. 每个请求带 request id。
2. 下载任务日志带 `task_id`、`user_id`、`stage`。
3. 不记录完整 token、cookie、预签名 URL、密码、secret。
4. 平台错误保留可排查摘要，但不把外部异常原文完整返回给用户。
5. Worker 关键阶段写入 `task_events`，用于任务详情和验收排查。

### 4.15 测试门禁

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
11. 视频源 registry、adapter factory 和 fallback 测试。
12. 全局响应 envelope 与 exception handler 测试。

### 4.16 渐进迁移顺序

后续实施建议分 8 个阶段：

1. `shared` 规范化：统一状态枚举、失败码和 selector 常量。
2. 全局响应与异常规范化：补齐 envelope、exception handlers、request id 和错误模型测试。
3. 视频源接入规范化：引入 adapter protocol、registry、factory 和 fallback。
4. 解析服务规范化：抽出 format domain、selector builder、parse adapter。
5. 任务服务规范化：引入 `TaskService` 和格式白名单校验。
6. Worker 规范化：抽出 options builder、download executor、artifact service。
7. Repository 收束：把任务、事件、用户和平台数据库访问移出 router/job。
8. 配置、日志和测试门禁收口：补齐 OpenAPI、pytest、健康检查和运行文档。

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
- 明确视频源接入使用 Adapter、Strategy、Registry、Factory 等设计模式约束。
- 明确全局响应数据格式、全局异常处理和错误码映射。
- 明确 SOLID、分层架构、契约优先、测试优先和复杂度控制要求。
- 覆盖解析、多分辨率选择、下载执行、失败分类、归档和测试门禁。
- 没有与 `docs/design/01-个人自部署万能视频下载器技术设计.md` 的状态机、对象存储和 API 边界冲突。

## 7. 风险与边界

1. 目录重构容易产生大量无行为变化 diff。实施时必须按阶段迁移，并用测试证明每阶段行为不变。
2. `yt-dlp` 平台适配受外部网站变化影响，后端只能稳定错误语义，不能承诺所有公网视频永久可解析。
3. 格式白名单需要在“安全限制”和“高级 raw 格式选择”之间平衡，首版应优先保证预设 selector 稳定。
4. Worker 下载和进度回写需要避免长事务和高频提交，否则可能影响 Postgres 性能。
5. Cookie 配置属于自部署增强能力，不能被设计成绕过付费、会员或访问控制的默认能力。
6. 全局响应 envelope 可能影响现有调用方，实施前必须明确兼容窗口和 OpenAPI 迁移策略。
7. 设计模式用于隔离变化，不应演化为过度抽象；每个新增抽象都必须由平台接入或测试替换需求驱动。

## 8. 待确认问题

1. 是否在下一阶段新增 `docs/plans/11-FastAPI后端结构规范化实施计划.md`，把本文档拆成可执行任务。
2. 是否保留 raw format 对普通任务创建开放，或只允许推荐与分辨率预设。
3. 是否把 `platform_profiles` 长期保留为代码配置，还是在后续阶段同步为数据库表。
4. 是否将既有 API 成功响应全量迁移为 envelope，还是只对新增 API 使用 envelope。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-16 | StephenQiu30 | 0.1.0 | 初始化 FastAPI 后端结构重设计与规范化方案 |
| 2026-06-16 | StephenQiu30 | 0.2.0 | 增补视频源接入设计模式、全局响应异常规范和软件工程约束 |
