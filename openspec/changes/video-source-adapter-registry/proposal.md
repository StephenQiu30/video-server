# Proposal: STE-309 视频源适配器与注册中心

## Why

当前 `download_adapter.py` 已实现 `PlatformAdapter`、`AdapterRegistry`、`YtDlpAdapter`、`BilibiliAdapter`、`DomesticShortVideoAdapter` 等适配器类，但缺少规范层定义。需要通过 OpenSpec 将适配器接口契约、注册中心规则、回退策略和失败映射规范化，为后续新增平台提供稳定基础，确保新增平台不修改 parse router 或任务创建主流程。

## What Changes

- 新增 OpenSpec spec `adapter-registry`：定义适配器接口契约、注册中心规则、回退策略、失败映射和格式模型
- 将 spec 推广到 `openspec/specs/` 作为当前事实层
- 创建 PRD06 `docs/prd/06-视频源接入与适配器扩展.md`
- 创建 PLAN11 `docs/plans/11-视频源适配器与注册中心计划.md`

## Capabilities

### New Capabilities

- `adapter-registry`: 视频源适配器注册中心规范，覆盖 PlatformAdapter 接口、AdapterRegistry 注册与匹配、YtDlpAdapter 回退、统一失败映射和格式模型

### Modified Capabilities

（无已有 spec 需要修改）

## Impact

- 受影响代码：`apps/api/app/services/download_adapter.py`、`apps/api/app/services/platforms.py`
- 受影响测试：`apps/api/tests/test_platform_adapters.py`、`apps/api/tests/test_platform_profiles.py`
- 受影响文档：`docs/prd/06-视频源接入与适配器扩展.md`、`docs/plans/11-视频源适配器与注册中心计划.md`
