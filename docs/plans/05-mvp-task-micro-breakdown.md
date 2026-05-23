---
layer: plans
doc_no: "PLAN-SERVER-005"
audience:
  - Dev
  - QA
purpose: "将 video-server 后端 MVP 重构按最小颗粒度进行执行分解。"
canonical_path: "docs/plans/05-mvp-task-micro-breakdown.md"
status: draft
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "video-server 现有 open issues 与测试"
outputs:
  - "可直接建 issue 的微任务清单"
triggers:
  - "MVP 后端任务开始"
  - "接口变更后验收补充"
downstream:
  - "docs/acceptance/01-backend-acceptance.md"
  - "docs/design/02-backend-runtime-design.md"
---

# video-server 任务微拆分

## Epic：E1 架构契约（P0）

- E1-S1：确认前后端本地联调端口与 CORS（跨域与回调地址统一）
- E1-S2：补齐 Auth/Parse/Tasks/Events/DownloadLink API 文档和字段注释

## Epic：E2 API-only（P0）

- E2-S1：`/api` 与 SPA 静态路由彻底分离的回归测试
- E2-S2：任务相关接口（列表、详情、取消、重试、事件）字段一致性测试
- E2-S3：`AppError` 响应结构统一与单测补全

## Epic：E3 平台适配（P0）

- E3-S1：下载引擎抽象接口回归测试（失败场景含受限内容）
- E3-S2：国内短视频 URL 解析适配与错误码映射测试
- E3-S3：yt-dlp 兜底测试与平台选择器单测

## Epic：E4 测试与 CI（P0）

- E4-S1：越权/边界测试（任务归属、下载链接失效）
- E4-S2：跨平台 smoke 策略补充与可选跳过策略说明
- E4-S3：CI 脚本与单测命令收敛

## Epic：E5 迁移收口（P0）

- E5-S1：迁移文档闭环与 review 门禁回归
- E5-S2：仓库边界梳理（AGENTS/README/ops）最终对齐
