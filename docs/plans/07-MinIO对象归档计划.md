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
status: draft
version: "1.0.0"
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
2. 建立 `task_artifacts` 索引。

## 3. 非目标

- 不处理下载链接签发和过期清理。

## 4. 核心内容

1. 定义对象 key 模板。
2. 实现产物上传与数据库索引写入。
3. 保证任务详情可以读取基础元数据和产物清单。

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/04-MinIO产物归档与下载交付.md`
2. `docs/design/01-个人自部署万能视频下载器技术设计.md`

### 5.2 输出文档

1. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

### 5.3 下游文档

1. `docs/plans/08-预签名下载与过期清理计划.md`

## 6. 验收门禁

- 任务成功后 MinIO 中可看到稳定对象路径。
- 产物索引与对象路径一致。

## 7. 风险与边界

对象 key 不稳定会影响调试、迁移和清理任务。

## 8. 待确认问题

- 是否将元数据另存为 JSON 文件。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN07 |
