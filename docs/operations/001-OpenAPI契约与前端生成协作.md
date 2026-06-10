---
layer: Operations
doc_no: "001"
audience:
  - Dev
  - QA
  - Ops
feature_area: openapi-frontend-contract
purpose: "定义 video-server OpenAPI 导出、前端生成协作和契约回归的长期操作规则。"
canonical_path: "docs/operations/001-OpenAPI契约与前端生成协作.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "scripts/export_openapi.py"
  - "apps/api/app/main.py"
outputs:
  - "OpenAPI 导出操作约定"
  - "前端生成协作入口"
triggers:
  - "API schema 发生变化"
  - "前端 video-web 需要重新生成 API client"
downstream:
  - "apps/api/tests/test_openapi_contract.py"
  - "video-web API client 生成流程"
---

# OpenAPI 契约与前端生成协作

## 1. 背景

`video-server` 通过 FastAPI 暴露 OpenAPI schema，前端 `video-web` 需要基于同一份契约生成或校验 API client。本文件沉淀导出、协作和回归检查规则。

## 2. 目标

1. 后端 API schema 变更后可以通过脚本导出。
2. 前端明确知道何时需要重新生成 API client。
3. CI 或本地测试能确认 OpenAPI 入口和关键响应模型存在。

## 3. 非目标

- 不在本仓库维护 `video-web` 的生成产物。
- 不替代具体接口 PRD、设计或测试计划。
- 不把一次性导出文件提交为长期事实，除非前后端协作明确需要。

## 4. 操作流程

1. 后端修改 schema、路由、响应模型或错误模型后，先运行后端契约测试。
2. 如需导出 schema，运行：

```bash
PYTHONPATH=apps/api python scripts/export_openapi.py
```

3. 前端仓库 `video-web` 根据导出的 OpenAPI schema 执行：

```bash
npm run api:generate
```

4. 前端生成后应检查类型变更、接口调用点和页面回归。

## 5. 验收门禁

- `/openapi.json`、`/docs`、`/redoc` 可访问。
- 核心响应模型 `ParseResponse`、`TaskRead`、`DownloadLinkResponse` 存在。
- PDF 和 SSE 等非 JSON 响应在 OpenAPI 中有明确 media type。
- 本文件路径被 `apps/api/tests/test_openapi_contract.py` 覆盖。

## 6. 风险与边界

OpenAPI 契约只能描述接口结构，不能证明业务行为正确。功能 PR 仍必须按对应 PRD 和测试计划补充业务测试。

## 7. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-02 | StephenQiu30 | 0.1.0 | 迁移 OpenAPI 协作说明到 operations 目录 |
