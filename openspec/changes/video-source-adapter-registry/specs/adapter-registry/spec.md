# Adapter Registry

## Purpose

定义视频源适配器注册中心的接口契约、注册规则、回退策略、失败映射和格式模型，确保新增视频源平台不修改 API 路由和任务创建主流程。

## ADDED Requirements

### Requirement: PlatformAdapter interface contract
每个视频源适配器 MUST 实现 `PlatformAdapter` 接口，包含 `supports()`、`parse()` 和 `map_parse_error()` 三个方法。

#### Scenario: Adapter supports matching URL
- **WHEN** `PlatformAdapter.supports(parsed_host)` 被调用，且 `parsed_host` 匹配该适配器的平台
- **THEN** 返回 `True`

#### Scenario: Adapter rejects non-matching URL
- **WHEN** `PlatformAdapter.supports(parsed_host)` 被调用，且 `parsed_host` 不匹配该适配器的平台
- **THEN** 返回 `False`

#### Scenario: Adapter parse returns ParseResponse
- **WHEN** `PlatformAdapter.parse(url)` 被调用，且 URL 可正常解析
- **THEN** 返回包含 `url`、`title`、`formats` 等字段的 `ParseResponse`

#### Scenario: Adapter maps parse errors to unified error codes
- **WHEN** `PlatformAdapter.map_parse_error(exc)` 被调用，且 `exc` 为解析异常
- **THEN** 返回包含统一错误码的 `AppError`

### Requirement: AdapterRegistry registration order
`AdapterRegistry` MUST 按注册顺序匹配适配器，专用适配器 MUST 在通用回退适配器之前。

#### Scenario: Registry matches specialized adapter first
- **WHEN** `AdapterRegistry.get_adapter(url)` 被调用，且 URL 匹配专用适配器
- **THEN** 返回专用适配器，而非 `YtDlpAdapter`

#### Scenario: Registry falls back to YtDlpAdapter
- **WHEN** `AdapterRegistry.get_adapter(url)` 被调用，且 URL 不匹配任何专用适配器
- **THEN** 返回 `YtDlpAdapter` 作为最终回退

### Requirement: YtDlpAdapter as universal fallback
`YtDlpAdapter` MUST 作为 `AdapterRegistry` 的最终回退适配器，处理所有未被专用适配器匹配的 URL。

#### Scenario: YtDlpAdapter supports any URL
- **WHEN** `YtDlpAdapter.supports(parsed_host)` 被调用
- **THEN** 始终返回 `True`

### Requirement: Unified failure mapping
所有适配器的 `map_parse_error()` MUST 将异常映射到统一的错误码体系。

#### Scenario: Restricted content maps to platform_restricted
- **WHEN** 异常消息包含 login/sign-in/members-only/private/premium/paid/drm/copyright/geo
- **THEN** 错误码为 `platform_restricted`，HTTP 状态码为 403

#### Scenario: Rate limiting maps to platform_rate_limited
- **WHEN** 异常消息包含 too many requests/429/rate limit/captcha
- **THEN** 错误码为 `platform_rate_limited`，HTTP 状态码为 429

#### Scenario: Unsupported URL maps to unsupported_platform
- **WHEN** 异常消息包含 unsupported url/no suitable extractor/no video formats
- **THEN** 错误码为 `unsupported_platform`，HTTP 状态码为 422

#### Scenario: Timeout maps to platform_unavailable
- **WHEN** 异常消息包含 timed out/timeout/connection reset/network unreachable
- **THEN** 错误码为 `platform_unavailable`，HTTP 状态码为 503

#### Scenario: Other errors map to parse_failed
- **WHEN** 异常不匹配任何已知特征
- **THEN** 错误码为 `parse_failed`，HTTP 状态码为 422

### Requirement: ParseResponse format model
所有适配器 MUST 返回 `ParseResponse`，其 `formats` 列表 MUST 包含至少一个推荐格式。

#### Scenario: ParseResponse contains recommended format
- **WHEN** 适配器成功解析 URL
- **THEN** `ParseResponse.formats` 包含至少一个 `kind=recommended` 的格式

#### Scenario: ParseResponse contains platform fields
- **WHEN** 适配器成功解析已注册平台的 URL
- **THEN** `ParseResponse` 包含 `platform_id`、`platform_category`、`compliance_note` 字段

### Requirement: New platform registration without router modification
新增视频源平台 MUST 只需添加 `PlatformProfile` 和 `PlatformAdapter`，不修改 parse router 或任务创建主流程。

#### Scenario: New platform auto-integrated
- **WHEN** 开发者添加新的 `PlatformProfile` 和 `PlatformAdapter` 子类
- **THEN** 该平台自动纳入解析和下载流程，无需修改 router 或主流程
