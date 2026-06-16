## ADDED Requirements

### Requirement: SourceAdapterRegistry registration
系统 SHALL 定义 `SourceAdapterRegistry` 类，支持以下操作：

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `register` | `(VideoSourceAdapter) -> None` | 注册适配器到链尾 |
| `register_first` | `(VideoSourceAdapter) -> None` | 注册适配器到链首 |
| `get_adapter` | `(SourceRequest) -> VideoSourceAdapter` | 选择匹配的适配器 |
| `list_adapters` | `() -> list[VideoSourceAdapter]` | 列出已注册适配器 |

#### Scenario: Register adapter and retrieve
- **WHEN** 调用 `register(BilibiliAdapter())` 后查询 bilibili URL
- **THEN** `get_adapter()` 返回 `BilibiliAdapter`

#### Scenario: Register first takes priority
- **WHEN** 先注册 `YtDlpAdapter`，再 `register_first(BilibiliAdapter())`
- **THEN** bilibili URL 优先匹配 `BilibiliAdapter`

### Requirement: Adapter selection by first match
`SourceAdapterRegistry.get_adapter()` SHALL 按注册顺序遍历适配器，返回第一个 `supports()` 返回 `True` 的适配器。

#### Scenario: First matching adapter wins
- **WHEN** 注册顺序为 `[DomesticShortVideoAdapter, BilibiliAdapter, YtDlpAdapter]`，查询 bilibili URL
- **THEN** 返回 `BilibiliAdapter`（`DomesticShortVideoAdapter.supports()` 返回 `False`）

#### Scenario: Fallback to last adapter
- **WHEN** URL 不匹配任何专用适配器
- **THEN** 返回 fallback 适配器（`YtDlpAdapter`）

### Requirement: Fallback chain
注册中心 SHALL 维护一个有序的降级链，当首选适配器失败时可尝试下一个适配器。降级链的默认顺序为：

1. `DomesticShortVideoAdapter`（国内短视频平台）
2. `BilibiliAdapter`（B 站）
3. `YtDlpAdapter`（通用 yt-dlp fallback）

#### Scenario: Unknown URL uses fallback
- **WHEN** 传入 `https://some-unknown-site.com/video/123`
- **THEN** `get_adapter()` 返回 `YtDlpAdapter`

#### Scenario: Blocked host rejected before adapter selection
- **WHEN** 传入 `http://localhost/video`
- **THEN** 在 adapter 选择前抛出 `AppError(ErrorCode.UNSAFE_URL)`

### Requirement: Registry default initialization
`SourceAdapterRegistry` SHALL 在无参构造时自动注册默认适配器链（`DomesticShortVideoAdapter` → `BilibiliAdapter` → `YtDlpAdapter`）。

#### Scenario: Default registry has three adapters
- **WHEN** 创建 `SourceAdapterRegistry()` 无参实例
- **THEN** `list_adapters()` 返回长度为 3 的列表

### Requirement: Platform-aware adapter selection
适配器选择 SHALL 基于 `SourceRequest.hostname` 与 `PlatformProfile.hosts` 的匹配，不在路由层做平台分支判断。

#### Scenario: No platform branches in router
- **WHEN** 新增视频源平台
- **THEN** 只需注册新适配器，无需修改 `routers/parse.py` 中的任何分支逻辑
