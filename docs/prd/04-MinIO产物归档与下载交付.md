---
layer: PRD
doc_no: "04"
audience:
  - PM
  - Dev
  - QA
  - Ops
feature_area: minio-archive-download-delivery
purpose: "定义 MinIO 产物归档、基础元数据保存、下载链接交付和过期清理边界。"
canonical_path: "docs/prd/04-MinIO产物归档与下载交付.md"
status: accepted
version: "1.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/03-异步下载任务主链路.md"
  - "docs/design/01-个人自部署万能视频下载器技术设计.md"
outputs:
  - "产物归档边界"
  - "下载交付策略"
triggers:
  - "新增产物类型"
  - "调整下载链接或过期策略"
downstream:
  - "docs/plans/07-MinIO对象归档计划.md"
  - "docs/plans/08-预签名下载与过期清理计划.md"
  - "docs/acceptance/01-个人自部署万能视频下载器验收方案.md"
---

# PRD04 MinIO 产物归档与下载交付

## 1. 背景

个人自部署下载器的价值不只是“下载成功”，而是把结果稳定保存下来，并能以受控方式交付给用户。首版必须把 MinIO 产物结构、预签名下载和过期清理定义清楚。

## 2. 目标

1. 主视频、封面和基础元数据有明确的归档位置。
2. 用户通过 API 获取短期有效的下载链接。
3. 文件过期后保留任务历史，但不再保留有效下载地址。

```gherkin
Given 一个下载任务已成功完成
When 用户请求下载链接
Then 系统返回短期有效的预签名 URL（默认 15 分钟）
And 任务详情包含 object_key、object_size、expires_at 等产物信息
```

```gherkin
Given 一个任务的产物已过期
When 用户查询任务详情或请求下载链接
Then 系统返回 retention_expired 错误
And 任务记录仍保留，但 object_key 已置空
```

## 3. 非目标

- 不做长期公共 CDN 分发。
- 不做跨用户共享下载链接。
- 不在首版中支持字幕、音频或 PDF 等增强产物。

## 4. 核心内容

### 4.1 必要产物

1. 主视频文件（存储于 MinIO，对象 key 为 `users/{user_id}/tasks/{task_id}/{filename}`）
2. 基础元数据：标题、时长、来源 URL、格式标识（存储于 `download_tasks` 表）
3. 增强产物（已实现）：AI 摘要、思维导图、字幕数据、视频元数据（存储于 `download_tasks` 表对应字段）

### 4.2 交付规则

1. 数据库存储对象索引和元数据，不直接存长期有效外链。
2. 访问下载文件时由 API 动态签发短期预签名链接（默认 TTL 15 分钟，可通过 `presigned_url_ttl_seconds` 配置）。
3. 文件保留时长由用户配置 `file_retention_hours`（默认 24 小时）决定。
4. 产物过期后任务详情仍可查询，但下载链接失效并提示已过期。
5. 过期清理在任务列表/详情查询时触发，清理后 `object_key` 置空，`failure_code` 设为 `retention_expired`。

### 4.3 产品边界

1. 主视频是成功任务的必要产物。
2. 基础元数据必须能从任务详情中读取。
3. 增强产物（AI 摘要、字幕、视频元数据）为可选，失败不影响主视频成功。
4. 产物索引直接存储于 `download_tasks` 表字段（`object_key`、`object_size`、`output_filename`、`expires_at`），不使用独立的 `task_artifacts` 表。

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/03-异步下载任务主链路.md`
2. `docs/design/01-个人自部署万能视频下载器技术设计.md`

### 5.2 输出文档

1. `docs/plans/07-MinIO对象归档计划.md`
2. `docs/plans/08-预签名下载与过期清理计划.md`

### 5.3 下游文档

1. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`
2. `docs/operations/01-个人自部署万能视频下载器运行与部署.md`

## 6. 验收门禁

- 主视频成功后可通过 `GET /api/tasks/{task_id}/download-link` 获得预签名链接（默认 15 分钟有效）。
- 任务详情返回基础元数据（标题、时长、URL、格式）和产物概览（object_key、object_size、output_filename、expires_at）。
- 过期后仍保留任务记录，但 `object_key` 置空、`failure_code` 为 `retention_expired`，不再返回有效下载地址。

## 7. 风险与边界

- MinIO 配置错误、对象命名不稳定或过期策略不一致，会直接影响用户取回结果和运维排障。
- 预签名链接依赖 `s3_public_endpoint_url` 配置；配置错误会导致链接无法访问。
- 过期清理在查询时触发，高并发场景下可能产生竞态。

## 8. 待确认问题

- ~~是否为封面单独暴露下载接口。~~ （已确认：封面通过 cover_url 字段存储，不单独提供下载接口）
- ~~过期时间是否允许部署者配置。~~ （已确认：通过用户级 `file_retention_hours` 配置，默认 24 小时）

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 重建 PRD04：MinIO 产物归档与下载交付 |
| 2026-06-10 | StephenQiu30 | 1.1.0 | 对齐实现：更新产物定义、交付规则、产品边界；确认待确认问题 |
