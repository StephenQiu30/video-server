---
layer: Plan
doc_no: "07"
audience:
  - Dev
  - QA
  - Ops
feature_area: minio-object-archive
purpose: "实现 PRD04 中的 MinIO 对象命名、产物索引和基础元数据归档。"
canonical_path: "docs/plans/07-MinIO对象归档计划.md"
status: approved
version: "1.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/04-MinIO产物归档与下载交付.md"
  - "docs/design/01-个人自部署万能视频下载器技术设计.md"
outputs:
  - "MinIO 对象归档计划"
triggers:
  - "需要落地产物持久化"
downstream:
  - "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
---

# PLAN07 MinIO 对象归档

## 1. 背景

主视频下载成功只是中间状态，只有归档到 MinIO 并建立索引后，任务结果才真正可交付。

## 2. 目标

1. 实现主视频、封面和元数据的对象命名规则。
2. 在 `download_tasks` 表上建立产物索引。

## 3. 非目标

- 不处理下载链接签发和过期清理（由 PLAN08 覆盖）。

## 4. 核心内容

### 4.1 对象 Key 模板

所有产物使用 `users/{user_id}/tasks/{task_id}/{filename}` 模式。该模式保证：

- 按用户隔离存储路径
- 按任务聚合产物
- 文件名保持原始扩展名

实现位置：`apps/worker/worker/artifact_storage.py`

### 4.2 产物上传流程

1. Worker 通过 yt-dlp 下载视频到本地工作目录。
2. ffprobe 校验文件大小和格式。
3. 调用 `ObjectStorage.upload_file(local_path, object_key, content_type)` 上传到 MinIO。
4. 设置 `DownloadTask` 字段：`object_key`、`object_size`、`expires_at`（当前时间 + `file_retention_hours`）。
5. 任务进入 `SUCCEEDED` 状态。

实现位置：`apps/worker/worker/jobs.py`、`apps/api/app/services/storage.py`

### 4.3 产物索引机制

产物信息直接存储在 `download_tasks` 表上，不使用独立的 `task_artifacts` 表：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `object_key` | Text | MinIO 对象路径 |
| `object_size` | BigInteger | 文件大小（字节） |
| `expires_at` | DateTime | 过期时间（UTC） |
| `output_filename` | String | 原始文件名 |

实现位置：`apps/api/app/models.py`

### 4.4 增强产物归档

AI 增强产物通过以下字段支持：

| 字段 | 说明 |
| --- | --- |
| `enhanced_status` | 增强处理状态 |
| `subtitle_data` | 字幕数据（JSON） |
| `video_metadata` | 视频元数据（JSON） |
| `ai_summary` | AI 摘要 |
| `ai_mindmap` | AI 思维导图 |

实现位置：`apps/api/app/models.py`

### 4.5 任务详情可读性

`GET /api/tasks/{task_id}` 返回 `TaskRead` schema，包含：

- `title`、`cover_url`、`duration_seconds`（基础元数据）
- `object_size`、`output_filename`、`expires_at`（产物信息）
- `ai_summary`、`ai_mindmap`、`ai_status`（AI 产物）
- `enhanced_status`、`subtitle_data`、`video_metadata`（增强产物）

实现位置：`apps/api/app/schemas.py`

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/04-MinIO产物归档与下载交付.md`
2. `docs/design/01-个人自部署万能视频下载器技术设计.md`

### 5.2 输出文档

1. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

### 5.3 下游文档

1. `docs/plans/08-预签名下载与过期清理计划.md`

## 6. 验收门禁

- 任务成功后 MinIO 中可看到 `users/{user_id}/tasks/{task_id}/{filename}` 格式的对象路径。
- 产物索引（`object_key`、`object_size`、`expires_at`）与对象路径一致。
- 任务详情返回 `title`、`cover_url`、`duration_seconds`、`object_size`、`output_filename`、`expires_at`。

## 7. 风险与边界

对象 key 不稳定会影响调试、迁移和清理任务。当前模式 `users/{user_id}/tasks/{task_id}/{filename}` 已固定，变更需评估影响。

## 8. 待确认问题

- 是否将元数据另存为 JSON 文件（当前不单独存储，通过 `video_metadata` 字段承载）。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN07 |
| 2026-06-10 | StephenQiu30 | 1.1.0 | 对齐实现：补充对象 key 模板、上传流程、索引机制、增强产物；状态改为 approved |
