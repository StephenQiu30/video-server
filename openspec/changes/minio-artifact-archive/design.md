## Context

视频下载器需要将 yt-dlp 下载的视频文件持久化到 MinIO 对象存储，并在数据库中建立索引，使任务结果可查询、可下载。当前 Worker 已具备下载和 ffprobe 校验能力，需要补齐归档和索引层。

## Goals / Non-Goals

**Goals:**
- 定义稳定的对象 Key 命名规则，保证路径可预测、可调试
- Worker 上传产物到 MinIO 后设置数据库索引字段
- 任务详情 API 返回完整产物元数据
- 支持增强产物（字幕、视频元数据）的归档

**Non-Goals:**
- 不处理预签名下载链接签发和过期清理（PLAN08 覆盖）
- 不做跨用户共享或公开分享链接
- 不单独存储元数据 JSON 文件

## Decisions

### 1. 对象 Key 使用 `users/{user_id}/tasks/{task_id}/{filename}` 模式

**选择**: 按用户 → 任务 → 文件名三级组织。

**理由**:
- 按用户隔离存储路径，便于配额管理和权限控制
- 按任务聚合产物，便于调试和清理
- 文件名保持原始扩展名，便于 Content-Type 推断

**替代方案**: 使用日期分区 `downloads/{yyyy}/{mm}/{dd}/` — 被拒绝，因为日期分区增加路径不稳定性，且不支持按用户/任务维度的高效查询。

### 2. 产物索引直接存储在 `download_tasks` 表

**选择**: 在 `DownloadTask` 模型上直接添加 `object_key`、`object_size`、`expires_at` 字段。

**理由**:
- 一个任务对应一个主视频文件，1:1 关系不需要独立表
- 减少 JOIN 查询，简化读取路径
- 与现有 `output_filename` 字段风格一致

**替代方案**: 独立 `task_artifacts` 表 — 被拒绝，因为增加复杂度而无实际收益。

### 3. 上传失败通过 `JobFailure` 机制传播

**选择**: `upload_artifact` 抛出 `JobFailure("storage_failed", ...)`，由 `_mark_failed` 捕获并设置 `failure_code`。

**理由**: 与现有下载失败、ffprobe 失败的错误处理机制一致，无需引入新的错误路径。

## Risks / Trade-offs

- [对象 Key 不稳定] → 当前模式已固定在 spec 中，变更需评估影响。缓解：Key 模式在 `artifact_storage.py` 中硬编码为单一函数。
- [MinIO 服务不可用] → 上传失败会让任务进入 FAILED 状态，用户可重试。缓解：`ensure_bucket` 在上传前自动创建 bucket。
- [文件名冲突] → 同一任务的文件名由 yt-dlp 输出决定，理论上可能重复。缓解：任务 ID 已保证唯一性，且 `output_filename` 记录最终文件名。

## Migration Plan

无需数据迁移 — 新字段通过 SQLAlchemy 模型定义，由 Alembic 或 `create_all` 自动创建。

## Open Questions

无。所有设计决策已在 PRD04 和 PLAN07 中确认。
