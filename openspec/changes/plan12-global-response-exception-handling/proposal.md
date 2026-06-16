# Proposal: PLAN12 全局响应与异常处理

## Problem

当前后端已有基础的 `failure_response` 工具函数和异常处理器，但存在以下不足：

1. 失败响应缺少 `request_id` 字段，无法在响应体中追踪请求链路。
2. 缺少统一的成功响应信封定义（当前直接返回业务数据）。
3. 请求上下文中间件未将 `request_id` 存入 `request.state`，导致异常处理器无法获取。
4. 响应模型未显式定义为包含 `request_id` 的信封结构。

## Goal

基于现有实现补全以下能力：

- 在 `failure_response` 信封中增加 `request_id` 字段。
- 确保请求上下文中间件将 `request_id` 存入 `request.state`。
- 异常处理器从 `request.state` 读取 `request_id` 并写入失败响应。
- 更新现有测试以验证 `request_id` 在失败响应中的存在性。
- 保持成功响应的向后兼容性（不改变现有成功响应结构）。

## Non-Goals

- 前端适配。
- 业务功能重写。
- 数据库 schema 改动。
- 将成功响应统一包装为 `{success: true, data: ...}` 信封（避免破坏现有调用方兼容性）。
- 新增分页响应模型（当前无分页需求）。

## Scope

### In Scope

- `apps/api/app/core/responses.py` — 失败响应信封增加 `request_id`
- `apps/api/app/middleware/request_context.py` — 存储 `request_id` 到 `request.state`
- `apps/api/app/core/errors.py` — 异常处理器传递 `request_id`
- `apps/api/tests/test_api_contract.py` — 更新失败响应断言
- `apps/api/tests/test_request_context_middleware.py` — 验证 `request.state` 存储

### Out of Scope

- 路由返回结构改造（当前路由已通过 `response_model` 直接返回业务数据）。
- 新增 OpenSpec spec 文件（此变更为增量补全，不改变已有 spec 基线）。
