## Why

主视频下载成功只是中间状态，只有归档到 MinIO 并建立索引后，任务结果才真正可交付。本 change 实现 PRD04 中的 MinIO 对象命名、产物索引和基础元数据归档，确保产物路径稳定、索引完整、任务详情可读。

## What Changes

- 定义对象 Key 模板 `users/{user_id}/tasks/{task_id}/{filename}`，按用户隔离、按任务聚合
- Worker 下载完成后通过 `ObjectStorage.upload_file()` 上传至 MinIO，设置 `object_key`、`object_size`、`expires_at`
- `download_tasks` 表直接存储产物索引字段，不使用独立 `task_artifacts` 表
- `TaskRead` schema 包含全部产物元数据：`title`、`cover_url`、`duration_seconds`、`object_size`、`output_filename`、`expires_at`
- 增强产物字段 `enhanced_status`、`subtitle_data`、`video_metadata` 支持 AI 摘要和字幕数据

## Capabilities

### New Capabilities

- `minio-artifact-archive`: MinIO 对象命名规则、产物上传流程、数据库索引机制和任务详情元数据完整性

### Modified Capabilities

（无既有 spec 需修改）

## Impact

- `apps/worker/worker/artifact_storage.py` — 对象 Key 生成和上传逻辑
- `apps/worker/worker/jobs.py` — 下载完成后的归档流程
- `apps/api/app/models.py` — `DownloadTask` 模型产物索引字段
- `apps/api/app/schemas.py` — `TaskRead` schema 元数据字段
- `apps/api/app/services/storage.py` — `ObjectStorage` 服务
- `apps/api/tests/test_task_endpoints.py` — 产物元数据和过期行为测试
