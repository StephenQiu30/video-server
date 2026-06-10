---
layer: Plan
doc_no: "07"
audience:
  - Dev
  - QA
  - Ops
feature_area: minio-object-archive
purpose: "实现 PRD04 中的 MinIO 对象命名、产物上传和基础元数据归档。"
canonical_path: "docs/plans/07-MinIO对象归档计划.md"
status: accepted
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
  - "docs/plans/08-预签名下载与过期清理计划.md"
  - "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
---

# PLAN07 MinIO 对象归档

## 1. 背景

主视频下载成功只是中间状态，只有归档到 MinIO 并在数据库中建立索引后，任务结果才真正可交付。产物归档发生在 Worker 下载流水线的后半段，是任务从 `running` 推进到 `succeeded` 的必要条件。

## 2. 目标

1. 定义稳定的对象命名规则，使产物路径可预测、可调试、可清理。
2. 实现主视频产物上传到 MinIO 并在 `download_tasks` 表上写入索引字段。
3. 保证任务详情接口可以读取基础元数据和产物概览。

## 3. 非目标

- 不处理下载链接签发和过期清理（见 PLAN08）。
- 不处理增强产物（字幕、封面文件）的 MinIO 归档（增强产物以 JSON 字段存储在数据库中）。

## 4. 核心内容

### 4.1 对象命名规则

对象 key 模板：

```text
users/{user_id}/tasks/{task_id}/{filename}
```

示例：

```text
users/1/tasks/550e8400-e29b-41d4-a716-446655440000/video.mp4
```

命名约束：

1. `user_id` 使用数据库中的用户主键（整数）。
2. `task_id` 使用 UUID 字符串（36 字符，含连字符）。
3. `filename` 由 `yt-dlp` 输出决定，通常包含视频标题和扩展名。
4. 对象 key 一旦写入不可变更，确保调试和清理路径稳定。

### 4.2 产物上传流程

上传发生在 Worker 流水线中，完整调用链：

```text
process_download_task (jobs.py)
  → download_task_artifact (download_runner.py)    # yt-dlp 下载到本地临时目录
  → assert_artifact_size (media_probe.py)          # 校验文件大小
  → probe_with_ffprobe (media_probe.py)            # 抽取时长、分辨率等元数据
  → upload_artifact (artifact_storage.py)          # 上传到 MinIO
  → 更新 DownloadTask 状态为 succeeded
```

`upload_artifact` 实现逻辑：

1. 构建对象 key：`users/{task.user_id}/tasks/{task.id}/{artifact.filename}`。
2. 调用 `ObjectStorage().upload_file(local_path, object_key)`。
3. 返回 `StoredArtifact(object_key, object_size, expires_at)`。
4. `expires_at` = 当前时间 + `user.file_retention_hours`。

`ObjectStorage.upload_file` 实现逻辑：

1. 确保 bucket 存在（`ensure_bucket`，幂等）。
2. 使用 `boto3` 的 `upload_file` 方法上传，设置 `ContentType`。
3. 使用 path-style addressing（`s3_force_path_style: True`）兼容 MinIO。

### 4.3 数据库索引

产物索引直接写在 `download_tasks` 表上，不使用独立的 `task_artifacts` 表：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `object_key` | `Text` | MinIO 对象路径，`None` 表示未归档或已过期清理 |
| `object_size` | `BigInteger` | 文件字节数 |
| `expires_at` | `DateTime(tz)` | 产物过期时间，基于用户 `file_retention_hours` 计算 |
| `output_filename` | `String(255)` | 原始文件名，用于下载时的 Content-Disposition |

任务成功后的写入顺序：

```python
task.state = "succeeded"
task.progress = 100
task.output_filename = artifact.filename
task.object_key = stored.object_key
task.object_size = stored.object_size
task.expires_at = stored.expires_at
```

### 4.4 基础元数据

基础元数据存储在 `download_tasks` 表字段中，不需要额外的 JSON 文件：

| 字段 | 来源 | 说明 |
| --- | --- | --- |
| `title` | yt-dlp / 用户传入 | 视频标题 |
| `duration_seconds` | ffprobe / yt-dlp | 视频时长 |
| `cover_url` | yt-dlp | 封面图片 URL（外部链接，不归档到 MinIO） |
| `format_id` | 用户选择 | 格式标识 |
| `format_label` | 用户选择 | 格式可读标签 |

任务详情接口 `GET /api/tasks/{task_id}` 通过 `TaskRead` schema 返回上述字段。

### 4.5 增强产物边界

增强产物（字幕、视频元数据 JSON）以 JSON 字符串存储在 `download_tasks` 表字段中，不上传到 MinIO：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `enhanced_status` | `String(32)` | 增强产物采集状态 |
| `subtitle_data` | `Text` | 字幕数据 JSON |
| `video_metadata` | `Text` | 视频技术元数据 JSON（分辨率、编码、码率等） |

增强产物采集失败不影响主任务的 `succeeded` 状态。

### 4.6 MinIO 配置

| 配置项 | 环境变量 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `s3_endpoint_url` | `S3_ENDPOINT_URL` | `http://127.0.0.1:9000` | 内部访问地址 |
| `s3_public_endpoint_url` | `S3_PUBLIC_ENDPOINT_URL` | `http://localhost:9000` | 预签名链接使用的地址 |
| `s3_access_key_id` | `S3_ACCESS_KEY_ID` | `minioadmin` | 访问密钥 ID |
| `s3_secret_access_key` | `S3_SECRET_ACCESS_KEY` | `minioadmin` | 访问密钥 |
| `s3_bucket` | `S3_BUCKET` | `video-downloads` | 存储桶名 |
| `s3_region` | `S3_REGION` | `us-east-1` | 区域 |
| `s3_force_path_style` | `S3_FORCE_PATH_STYLE` | `True` | 路径样式寻址（MinIO 必需） |

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/04-MinIO产物归档与下载交付.md`
2. `docs/design/01-个人自部署万能视频下载器技术设计.md`

### 5.2 输出文档

1. `docs/plans/08-预签名下载与过期清理计划.md`
2. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

### 5.3 下游文档

1. `docs/operations/01-个人自部署万能视频下载器运行与部署.md`

## 6. 验收门禁

- 任务成功后 MinIO 中可看到 `users/{user_id}/tasks/{task_id}/{filename}` 路径的对象。
- `download_tasks` 表中 `object_key`、`object_size`、`expires_at` 与 MinIO 实际状态一致。
- 任务详情接口返回 `title`、`duration_seconds`、`output_filename`、`object_size`。
- 封面缺失（`cover_url` 为 `None`）不影响任务成功。

## 7. 风险与边界

1. 对象 key 不稳定会影响调试、迁移和清理。key 一旦写入 `download_tasks.object_key` 后不可变更。
2. `ensure_bucket` 在每次上传前调用，依赖 MinIO 可用性。MinIO 不可用会导致 `storage_failed` 错误码。
3. `cover_url` 存储的是外部 URL 而非 MinIO 对象 key，过期或失效后无法通过本系统恢复。

## 8. 待确认问题

- 是否将增强产物（字幕、元数据 JSON）也上传到 MinIO 而非仅存数据库字段。
- 是否支持自定义对象 key 前缀（如按日期分目录）。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN07 |
| 2026-06-10 | StephenQiu30 | 1.1.0 | 补充对象命名规则、上传流程、数据库索引、元数据归档和配置项 |
