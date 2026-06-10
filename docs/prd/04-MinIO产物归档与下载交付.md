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
status: approved
version: "1.0.0"
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
When 用户查询任务结果
Then 系统返回视频、封面和元数据概览
And 下载链接通过受控的预签名方式提供
```

## 3. 非目标

- 不做长期公共 CDN 分发。
- 不做跨用户共享下载链接。
- 不做公开分享链接。

## 4. 核心内容

### 4.1 必要产物

1. 主视频文件
2. 标题、作者、时长、来源平台
3. 封面，可用则保存

### 4.2 交付规则

1. 数据库存储对象索引和元数据（`object_key`、`object_size`、`expires_at`），不直接存长期有效外链。
2. 访问下载文件时由 API 动态签发短期预签名链接（默认 TTL 900 秒，可配置）。
3. 产物过期后任务详情仍可查询，但下载链接失效并提示已过期（HTTP 410，`retention_expired`）。
4. 过期清理后任务保持 `SUCCEEDED` 状态，`object_key` 置空，`failure_code` 设为 `retention_expired`。

### 4.3 产品边界

1. 主视频是成功任务的必要产物。
2. 封面不可得时 `cover_url` 为空，不影响主视频成功。
3. 基础元数据（`title`、`cover_url`、`duration_seconds`、`object_size`、`output_filename`、`expires_at`）必须能从任务详情中读取。
4. 增强产物（AI 摘要、字幕、视频元数据）已通过 `enhanced_status`、`subtitle_data`、`video_metadata` 字段支持。

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

- 主视频成功后可通过下载接口获得预签名链接。
- 任务详情返回基础元数据和产物概览。
- 过期后仍保留任务记录，但不再返回有效下载地址。

## 7. 风险与边界

MinIO 配置错误、对象命名不稳定或过期策略不一致，会直接影响用户取回结果和运维排障。

## 8. 待确认问题

- 是否为封面单独暴露下载接口。
- 过期时间是否允许部署者配置。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 重建 PRD04：MinIO 产物归档与下载交付 |
| 2026-06-10 | StephenQiu30 | 1.1.0 | 对齐实现：更新交付规则、产品边界、非目标；状态改为 approved |
