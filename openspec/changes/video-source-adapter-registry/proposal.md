## Why

当前后端的视频解析逻辑以 `services/download_adapter.py` 中的非正式适配器模式运行，所有适配器硬编码在 `AdapterRegistry` 默认列表中，缺乏统一的领域模型、注册协议和扩展机制。新增视频源需要修改核心模块并手动维护适配器顺序，无法按统一协议快速接入。本次改造将平台分支式解析演进为 Strategy + Adapter + Registry 的可扩展结构，为后续多源接入奠定基础。

## What Changes

- 定义视频源领域对象（`SourceRequest`、`SourceContext`、`SourceInfo`、`MediaVariant`、`SubtitleTrack`、`SourceCapability`），替代当前 `ParsedHost` + 直接返回 `ParseResponse` 的耦合模式。
- 定义 `VideoSourceAdapter` 抽象协议与 `SourceAdapterRegistry` 注册/选择/降级机制，替代当前 `PlatformAdapter` + `AdapterRegistry` 的硬编码列表。
- 将现有 `YtDlpAdapter`、`BilibiliAdapter`、`DomesticShortVideoAdapter` 迁移为新协议实现。
- 创建统一 `ParseService`，将 `/api/parse` 路由和后续下载任务接入注册中心，替代当前 `DownloadEngineAdapter` 直接调用。
- 适配器错误统一映射到 `ErrorCode`，避免原始异常外泄。

## Capabilities

### New Capabilities

- `video-source-adapter`: 定义视频源适配器协议（`VideoSourceAdapter` ABC）、领域对象（`SourceRequest`、`SourceContext`、`SourceInfo`、`MediaVariant`、`SubtitleTrack`、`SourceCapability`）和错误映射规范。
- `source-adapter-registry`: 定义适配器注册中心（`SourceAdapterRegistry`）的注册、选择、降级链路和 fallback 策略。
- `parse-service`: 定义统一解析服务（`ParseService`）的职责、输入输出契约和与 `/api/parse` 路由的集成规范。

### Modified Capabilities

- `platform-profiles`: 适配器选择将基于 `PlatformProfile` 的 `hosts` 匹配，但不再在路由层做平台分支判断。规范层面无需求变更，仅实现层耦合方式调整。

## Impact

- **新增模块**: `apps/api/app/sources/`（领域模型、适配器协议、注册中心、平台适配器实现）
- **新增服务**: `apps/api/app/services/parse_service.py`
- **修改路由**: `apps/api/app/routers/parse.py`（改用 `ParseService`，移除直接 `DownloadEngineAdapter` 调用）
- **新增测试**: `apps/api/tests/sources/`、`apps/api/tests/test_parse_service.py`
- **保留兼容**: `ParseResponse` schema 不变，API 契约向后兼容
- **依赖**: 无新增外部依赖，仅重组内部模块
