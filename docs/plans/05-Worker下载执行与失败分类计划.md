---
layer: Plan
doc_no: "05"
audience:
  - Dev
  - QA
feature_area: worker-download-classification
purpose: "实现 PRD03 中的 Worker 下载执行、状态推进和失败分类。"
canonical_path: "docs/plans/05-Worker下载执行与失败分类计划.md"
status: draft
version: "1.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/03-异步下载任务主链路.md"
  - "docs/design/01-个人自部署万能视频下载器技术设计.md"
outputs:
  - "Worker 下载执行计划"
triggers:
  - "需要落地异步执行主链路"
downstream:
  - "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
---

# PLAN05 Worker 下载执行与失败分类

## 1. 背景

异步任务只有真正被 Worker 消费、下载、上传并回写状态，主链路才算成立。

## 2. 目标

1. 接入 Redis Queue 和 Worker 消费逻辑。
2. 调用 `yt-dlp` 下载主视频和基础元数据。
3. 对常见失败建立稳定分类。

## 3. 非目标

- 不处理取消、重试和事件流细节。

## 4. 核心内容

### 4.1 Worker 执行流程

1. RQ Worker 从 Redis Queue 拾取任务。
2. 更新任务状态为 `running`，写入 `task_events`。
3. 调用 `yt-dlp` 下载视频到临时目录。
4. 调用 `ffprobe` 探查媒体信息。
5. 上传产物到 MinIO。
6. 更新任务状态为 `succeeded`，`progress = 100`。
7. 写入 `object_key`、`object_size`、`expires_at`。
8. 清理临时文件。

### 4.2 失败分类机制

Worker 通过 `failure_code()` 函数将异常映射到 `WorkerFailureCode` 枚举：

| 异常特征 | 错误码 | 可重试 |
| --- | --- | --- |
| `requested format is not available` | `format_unavailable` | 否 |
| `file is larger than max-filesize` | `file_too_large` | 否 |
| `timed out` / `timeout` | `task_timeout` | 是 |
| `unsupported url` / `no video formats found` | `unsupported_platform` | 否 |
| 浏览器 Cookie 相关关键词 | `browser_cookies_unavailable` | 否 |
| 其他下载异常 | `download_failed` | 是 |

特殊处理：
- `JobFailure(TASK_CANCELED)` → `task_canceled`（用户取消）
- `JobFailure(STORAGE_FAILED)` → `storage_failed`（MinIO 上传失败，可重试）

### 4.3 失败信息格式化

`format_failure_reason()` 将异常转换为用户可读消息：
- 浏览器 Cookie 错误：提示用户确认 Chrome 登录态
- 格式不可用：提示选择其他清晰度
- 不支持平台：提示换用公开视频链接
- 其他：截取异常首行，脱敏 URL，限制 300 字符

### 4.4 关键实现文件

| 文件 | 职责 |
| --- | --- |
| `apps/worker/worker/jobs.py` | Worker 任务入口和编排 |
| `apps/worker/worker/domain.py` | 领域类型（WorkerStage、WorkerFailureCode、FailureInfo） |
| `apps/worker/worker/failures.py` | 失败分类和格式化 |
| `apps/worker/worker/adapters/` | yt-dlp、MinIO、Redis 封装 |

### 4.5 Worker 阶段定义

| 阶段 | 含义 |
| --- | --- |
| `start` | 任务开始 |
| `download` | yt-dlp 下载中 |
| `probe` | ffprobe 媒体探查 |
| `upload` | MinIO 上传 |
| `ai` | AI 增强处理（可选） |
| `cleanup` | 临时文件清理 |

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/03-异步下载任务主链路.md` — §4.3 错误码目录、§4.4 进度语义
2. `docs/design/01-个人自部署万能视频下载器技术设计.md` — §4.1 总体架构

### 5.2 输出文档

1. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

### 5.3 下游文档

1. `docs/plans/07-MinIO对象归档计划.md`

## 6. 验收门禁

- Worker 成功推进状态并完成主视频下载。
- 常见失败返回稳定错误码。
- 失败消息面向用户可理解，不泄露敏感参数。

## 7. 风险与边界

第三方平台变化会直接影响下载适配器，失败分类不能过度依赖单一异常文本。

## 8. 待确认问题

- 是否为限流和平台受限分别定义错误码。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN05 |
| 2026-06-11 | StephenQiu30 | 1.1.0 | 补充详细实现内容：执行流程、失败分类机制、失败信息格式化、关键文件、阶段定义 |
