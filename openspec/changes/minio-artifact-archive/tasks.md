## 1. 对象 Key 命名与上传

- [x] 1.1 在 `apps/worker/worker/artifact_storage.py` 实现 `upload_artifact(task, artifact)` 函数，生成 `users/{user_id}/tasks/{task_id}/{filename}` 格式的 object_key
- [x] 1.2 在 `apps/worker/worker/artifact_storage.py` 实现 `delete_artifact(object_key)` 函数
- [x] 1.3 在 `apps/worker/worker/domain.py` 定义 `StoredArtifact` 数据类（object_key, object_size, expires_at）

## 2. Worker 归档流程

- [x] 2.1 在 `apps/worker/worker/jobs.py` 的 `process_download_task` 中，下载和 ffprobe 校验后调用 `upload_artifact`
- [x] 2.2 上传成功后设置 `DownloadTask` 的 `object_key`、`object_size`、`expires_at`、`output_filename` 字段
- [x] 2.3 任务状态设为 `SUCCEEDED`，进度设为 100
- [x] 2.4 上传失败时通过 `JobFailure("storage_failed", ...)` 传播，由 `_mark_failed` 处理

## 3. 数据库模型

- [x] 3.1 在 `apps/api/app/models.py` 的 `DownloadTask` 上添加 `object_key`（Text）、`object_size`（BigInteger）、`expires_at`（DateTime）字段
- [x] 3.2 添加增强产物字段：`enhanced_status`、`subtitle_data`、`video_metadata`

## 4. API Schema 与路由

- [x] 4.1 在 `apps/api/app/schemas.py` 的 `TaskRead` 中包含 `object_size`、`output_filename`、`expires_at` 字段
- [x] 4.2 在 `TaskRead` 中包含增强产物字段：`enhanced_status`、`subtitle_data`、`video_metadata`
- [x] 4.3 确认 `GET /api/tasks/{task_id}` 返回完整产物元数据

## 5. 测试验证

- [x] 5.1 `test_succeeded_task_exposes_state_progress_and_download_fields` — 验证 SUCCEEDED 任务返回 object_size、output_filename、expires_at
- [x] 5.2 `test_task_detail_returns_metadata_completeness` — 验证 title、cover_url、duration_seconds、object_size、output_filename、expires_at 完整性
- [x] 5.3 `test_cleanup_expired_task_outputs_nullifies_key_and_sets_retention_expired` — 验证过期清理后 object_key 置空
- [x] 5.4 `test_download_link_rejects_missing_object_key` — 验证 object_key 为空时返回 410
- [x] 5.5 `npm test` 全量通过（166 passed）
