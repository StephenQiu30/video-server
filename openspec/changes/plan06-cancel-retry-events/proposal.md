---
change: plan06-cancel-retry-events
status: draft
created: 2026-06-10
ticket: STE-268
---

# PLAN06 取消、重试与事件流 — 生产加固

## 背景

取消、重试和事件流的核心功能已在 prior tickets 中实现并通过测试覆盖。本 change 聚焦于生产环境加固和可观察性补全。

## 目标

1. 将 `task_events` 表创建加入 `UPGRADES` 迁移列表，确保已有生产 DB 不遗漏该表。
2. Worker 检测到取消时记录事件日志，补全取消路径的可观察性。
3. 更新 PLAN06 状态为已实现。

## 非目标

- 不实现 SSE 推送（沿用现有轮询方案）。
- 不新增自动重试逻辑（重试保持用户主动触发）。
- 不引入结构化 event_type 字段（当前 state+message 方案满足需求）。

## 已有实现摘要

| 能力 | 状态 | 关键文件 |
| --- | --- | --- |
| 取消接口 | 已实现 | `services/tasks.py:cancel_task` |
| 重试接口 | 已实现 | `services/tasks.py:retry_task` |
| 事件落库 | 已实现 | `models.py:TaskEvent`, `services/tasks.py:add_task_event` |
| 失败分类 | 已实现 | `worker/domain.py`, `worker/failures.py` |
| Worker 取消协作 | 已实现 | `worker/jobs.py:_is_canceled` |
| 事件查询接口 | 已实现 | `routers/tasks.py:GET /api/tasks/{id}/events` |

## 待完成工作

### 1. 数据库迁移加固

在 `apps/api/app/db/upgrade.py` 的 `UPGRADES` 列表中追加 `task_events` 表及其索引的创建语句，使用 `IF NOT EXISTS` 保证幂等。

### 2. Worker 取消检测事件

在 `apps/worker/worker/jobs.py` 的 `process_download_task` 中，当 `_is_canceled` 返回 True 导致提前退出时，记录一条 `CANCELED` 事件说明 Worker 检测到取消并停止执行。

### 3. 文档状态更新

将 `docs/plans/06-取消重试与事件流计划.md` 的 status 从 `draft` 更新为 `implemented`。

## 验证方式

1. 运行现有测试套件确认无回归：`cd apps/api && python -m pytest tests/`
2. 新增测试验证 Worker 取消检测事件落库
3. 检查 UPGRADES 列表包含 task_events 表创建语句
