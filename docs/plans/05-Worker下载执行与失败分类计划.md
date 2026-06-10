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
version: "1.0.0"
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

1. 实现 `queued -> running -> succeeded/failed` 状态流转。
2. 将下载失败、上传失败映射到业务错误码。
3. 完成 Worker 侧最小验证路径。

## 5. 关联文档

### 5.1 输入文档

1. `docs/prd/03-异步下载任务主链路.md`
2. `docs/design/01-个人自部署万能视频下载器技术设计.md`

### 5.2 输出文档

1. `docs/acceptance/01-个人自部署万能视频下载器验收方案.md`

### 5.3 下游文档

1. `docs/plans/07-MinIO对象归档计划.md`

## 6. 验收门禁

- Worker 成功推进状态并完成主视频下载。
- 常见失败返回稳定错误码。

## 7. 风险与边界

第三方平台变化会直接影响下载适配器，失败分类不能过度依赖单一异常文本。

## 8. 待确认问题

- 是否为限流和平台受限分别定义错误码。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化 PLAN05 |
