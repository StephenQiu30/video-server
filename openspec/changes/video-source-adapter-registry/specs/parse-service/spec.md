## ADDED Requirements

### Requirement: ParseService unified entry point
系统 SHALL 定义 `ParseService` 类，作为视频解析的统一入口，替代当前 `DownloadEngineAdapter` 的直接调用。

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `parse` | `(url: str, format_id: str \| None = None) -> ParseResponse` | 解析视频 URL 并返回标准响应 |

#### Scenario: ParseService delegates to registry
- **WHEN** 调用 `ParseService().parse("https://www.bilibili.com/video/BV1xx411c7mD")`
- **THEN** 通过注册中心选择 `BilibiliAdapter`，返回 `ParseResponse`

#### Scenario: ParseService with format_id
- **WHEN** 调用 `parse(url, format_id="best")`
- **THEN** `SourceRequest.format_id` 传递给适配器

### Requirement: ParseService error handling
`ParseService.parse()` SHALL 捕获适配器抛出的所有异常，通过适配器的 `map_error()` 方法映射为 `AppError`，避免原始异常外泄。

#### Scenario: Adapter exception mapped to AppError
- **WHEN** 适配器抛出 `RuntimeError("need to login")`
- **THEN** `ParseService.parse()` 抛出 `AppError(ErrorCode.PLATFORM_RESTRICTED)`

#### Scenario: AppError passes through
- **WHEN** 适配器直接抛出 `AppError`
- **THEN** `ParseService.parse()` 不做二次映射，直接抛出

### Requirement: ParseService response conversion
`ParseService.parse()` SHALL 将 `SourceInfo` 转换为 `ParseResponse`，保持与现有 API 契约完全兼容。

#### Scenario: ParseResponse fields preserved
- **WHEN** 解析 bilibili URL
- **THEN** `ParseResponse` 包含 `url`、`title`、`cover_url`、`duration_seconds`、`source_site`、`platform_id`、`platform_category`、`compliance_note`、`extractor`、`watermark_hint`、`formats`

#### Scenario: Multi-resolution presets in response
- **WHEN** 源提供 1080p 视频
- **THEN** `ParseResponse.formats` 包含推荐格式和 1080p/720p/480p/360p 预设

### Requirement: Router integration without platform branches
`routers/parse.py` SHALL 调用 `ParseService.parse()` 而非直接调用 `DownloadEngineAdapter`，且不包含任何平台判断分支代码。

#### Scenario: Router delegates to ParseService
- **WHEN** POST `/api/parse` 收到请求
- **THEN** 路由调用 `ParseService().parse(normalize_user_url(payload.url))`

#### Scenario: No platform branches in router
- **WHEN** 审查 `routers/parse.py` 源码
- **THEN** 不包含 `if "bilibili" in url` 或类似的平台判断逻辑

### Requirement: Rate limiting preserved
`/api/parse` 路由 SHALL 保持现有的速率限制逻辑不变。

#### Scenario: Rate limiter still active
- **WHEN** 用户超过速率限制
- **THEN** 返回速率限制错误，与改造前行为一致
