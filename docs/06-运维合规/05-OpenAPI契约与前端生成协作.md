---
layer: Operations
doc_no: "06-05"
audience:
  - Backend
  - Frontend
  - QA
  - Ops
feature_area: openapi-contract
purpose: "定义 video-server 的 Swagger/OpenAPI 契约导出、前端生成协作方式和上线前检查口径。"
canonical_path: "docs/06-运维合规/05-OpenAPI契约与前端生成协作.md"
status: active
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "apps/api/app/main.py"
  - "apps/api/app/routers/"
  - "apps/api/app/schemas.py"
outputs:
  - "scripts/export_openapi.py"
  - "video-web/docs/openapi/video-server.openapi.json"
triggers:
  - "新增、删除或调整后端公开 API"
  - "前端需要重新生成 API client"
  - "发布前执行接口契约回归"
downstream:
  - "video-web npm run api:generate"
  - "apps/api/tests/test_openapi_contract.py"
---

# OpenAPI 契约与前端生成协作

## 1. 背景

`video-server` 作为前后端分离后的 API 服务，需要提供稳定、可检查、可导出的 OpenAPI 契约，供 `video-web` 生成 TypeScript API client。契约变化必须先通过后端测试验收，再同步给前端生成，避免前端手写接口漂移。

## 2. 目标

1. 后端本地必须可访问 Swagger UI、ReDoc 和 `/openapi.json`。
2. 核心业务接口必须声明 response model 或明确的非 JSON 响应类型。
3. 后端必须提供无需启动 HTTP 服务的契约导出脚本。
4. 前端以导出的 OpenAPI 文件为输入执行 `npm run api:generate`。

## 3. 非目标

- 不在后端仓库生成或提交前端 TypeScript client。
- 不把 OpenAPI 导出文件作为唯一真实来源；真实来源仍是 FastAPI router 与 Pydantic schema。
- 不在本阶段引入 API 网关、服务发现或多版本 API 发布机制。

## 4. 协作流程

后端变更公开接口后，先运行契约测试：

```bash
PYTHONPATH=apps/api:apps/worker:packages/shared pytest apps/api/tests/test_openapi_contract.py
```

需要导出契约时，在 `video-server` 仓库执行：

```bash
python scripts/export_openapi.py ../video-web/docs/openapi/video-server.openapi.json
```

然后切换到 `video-web` 仓库执行：

```bash
npm run api:generate
npm run api:check
```

如果后端只调整内部实现，不改变路径、请求体、响应体、状态码或鉴权语义，不需要同步前端生成文件。

## 5. 后端契约要求

1. JSON API 使用 Pydantic schema 声明 `response_model`。
2. PDF 下载、SSE 任务流、OAuth Redirect 等非 JSON 响应必须在 OpenAPI `responses` 中声明 media type 和状态码。
3. 健康检查与 readiness 接口也必须保留明确 schema，便于部署系统和前端诊断页复用。
4. 管理端统计接口必须返回稳定字段，不返回无约束 `dict`。

## 6. 验收门禁

- `/openapi.json` 返回 200。
- `/docs` 和 `/redoc` 返回 200。
- `apps/api/tests/test_openapi_contract.py` 通过。
- `scripts/export_openapi.py` 可以输出到指定路径。
- `video-web` 可以基于导出文件执行 `npm run api:generate`。

## 7. 风险与边界

- 导出的 OpenAPI 文件是前端生成输入，不替代后端测试。
- OAuth callback 实际返回重定向，不能被错误声明为 JSON token。
- SSE 和 PDF 端点不应被前端生成工具误判为普通 JSON API。

## 8. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-05-23 | StephenQiu30 | 0.1.0 | 初始化 OpenAPI 契约导出与前端生成协作说明 |
