## ADDED Requirements

### Requirement: SourceRequest domain object
系统 SHALL 定义 `SourceRequest` 冻结数据类，包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `url` | `str` | ✅ | 原始用户输入 URL |
| `normalized_url` | `str` | ✅ | 归一化后的 URL |
| `hostname` | `str` | ✅ | 提取的小写 hostname |
| `format_id` | `str \| None` | ❌ | 用户选择的格式标识 |

#### Scenario: Create SourceRequest from valid URL
- **WHEN** 传入 `https://www.bilibili.com/video/BV1xx411c7mD`
- **THEN** 返回 `SourceRequest`，`hostname` 为 `www.bilibili.com`，`normalized_url` 与输入一致

#### Scenario: SourceRequest rejects empty hostname
- **WHEN** 传入无法提取 hostname 的 URL
- **THEN** 抛出 `AppError(ErrorCode.INVALID_URL)`

### Requirement: SourceContext domain object
系统 SHALL 定义 `SourceContext` 冻结数据类，包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `request` | `SourceRequest` | ✅ | 原始请求 |
| `platform_profile` | `PlatformProfile \| None` | ❌ | 匹配的平台画像 |
| `adapter_name` | `str` | ✅ | 选中的适配器名称 |

#### Scenario: SourceContext carries platform profile
- **WHEN** URL 匹配 bilibili 平台
- **THEN** `platform_profile` 不为 `None`，`platform_profile.id` 为 `bilibili`

#### Scenario: SourceContext with unknown platform
- **WHEN** URL 不匹配任何已知平台
- **THEN** `platform_profile` 为 `None`，`adapter_name` 为 fallback 适配器名

### Requirement: SourceInfo domain object
系统 SHALL 定义 `SourceInfo` 冻结数据类，作为适配器解析结果，包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `title` | `str \| None` | ❌ | 视频标题 |
| `cover_url` | `str \| None` | ❌ | 封面图 URL |
| `duration_seconds` | `int \| None` | ❌ | 时长（秒） |
| `extractor` | `str \| None` | ❌ | yt-dlp extractor 名称 |
| `variants` | `list[MediaVariant]` | ✅ | 可用媒体变体列表 |
| `subtitles` | `list[SubtitleTrack]` | ✅ | 字幕轨道列表 |
| `capabilities` | `set[SourceCapability]` | ✅ | 源支持的能力集合 |
| `raw_info` | `dict[str, Any]` | ✅ | 原始 yt-dlp info dict |

#### Scenario: SourceInfo populated from yt-dlp result
- **WHEN** yt-dlp 返回包含 title、duration、formats 的 info dict
- **THEN** `SourceInfo` 的 `title`、`duration_seconds`、`variants` 正确映射

#### Scenario: SourceInfo with empty formats
- **WHEN** yt-dlp 返回空 formats 列表
- **THEN** `variants` 为空列表，`capabilities` 不含 `HAS_VIDEO`

### Requirement: MediaVariant domain object
系统 SHALL 定义 `MediaVariant` 冻结数据类，表示一个可下载的媒体变体：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `format_id` | `str` | ✅ | 格式标识 |
| `ext` | `str \| None` | ❌ | 文件扩展名 |
| `resolution` | `str \| None` | ❌ | 分辨率字符串 |
| `height` | `int \| None` | ❌ | 视频高度 |
| `width` | `int \| None` | ❌ | 视频宽度 |
| `filesize` | `int \| None` | ❌ | 文件大小（字节） |
| `vcodec` | `str \| None` | ❌ | 视频编码 |
| `acodec` | `str \| None` | ❌ | 音频编码 |
| `stream_type` | `Literal["video+audio", "video-only", "audio-only"] \| None` | ❌ | 流类型 |

#### Scenario: MediaVariant from video+audio format
- **WHEN** 格式有 vcodec 和 acodec（均非 "none"）
- **THEN** `stream_type` 为 `video+audio`

#### Scenario: MediaVariant from video-only format
- **WHEN** 格式 vcodec 非 "none" 且 acodec 为 "none"
- **THEN** `stream_type` 为 `video-only`

#### Scenario: MediaVariant from audio-only format
- **WHEN** 格式 vcodec 为 "none"
- **THEN** `stream_type` 为 `audio-only`

### Requirement: SubtitleTrack domain object
系统 SHALL 定义 `SubtitleTrack` 冻结数据类：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `language` | `str` | ✅ | 语言代码 |
| `ext` | `str \| None` | ❌ | 字幕格式扩展名 |
| `url` | `str \| None` | ❌ | 字幕下载 URL |

#### Scenario: SubtitleTrack from yt-dlp subtitles
- **WHEN** yt-dlp info 包含 subtitles 字段
- **THEN** 每个字幕轨道映射为一个 `SubtitleTrack`

### Requirement: SourceCapability enum
系统 SHALL 定义 `SourceCapability` 枚举，包含以下值：

| 值 | 说明 |
| --- | --- |
| `HAS_VIDEO` | 源包含视频流 |
| `HAS_AUDIO` | 源包含音频流 |
| `HAS_SUBTITLES` | 源包含字幕 |
| `MULTI_RESOLUTION` | 源提供多分辨率 |

#### Scenario: Capability detection from formats
- **WHEN** formats 列表包含有 vcodec 的格式
- **THEN** `capabilities` 包含 `HAS_VIDEO`

### Requirement: VideoSourceAdapter protocol
系统 SHALL 定义 `VideoSourceAdapter` 抽象基类，包含以下方法：

| 方法 | 签名 | 说明 |
| --- | --- | --- |
| `name` | `str` 属性 | 适配器唯一名称 |
| `supports` | `(SourceRequest) -> bool` | 判断是否支持该请求 |
| `parse` | `(SourceRequest) -> SourceInfo` | 解析视频源信息 |
| `map_error` | `(Exception) -> AppError` | 将异常映射为统一错误 |

#### Scenario: Adapter supports matching URL
- **WHEN** `BilibiliAdapter.supports()` 收到 bilibili URL
- **THEN** 返回 `True`

#### Scenario: Adapter rejects non-matching URL
- **WHEN** `BilibiliAdapter.supports()` 收到 youtube URL
- **THEN** 返回 `False`

#### Scenario: Adapter parse returns SourceInfo
- **WHEN** `adapter.parse(request)` 成功执行
- **THEN** 返回包含 `variants` 和 `capabilities` 的 `SourceInfo`

#### Scenario: Adapter maps restricted error
- **WHEN** yt-dlp 抛出 "need to login" 异常
- **THEN** `map_error()` 返回 `AppError(ErrorCode.PLATFORM_RESTRICTED)`

### Requirement: Adapter error mapping
每个适配器的 `map_error()` 方法 SHALL 将以下异常类型映射到对应 `ErrorCode`：

| 异常特征 | ErrorCode | HTTP Status |
| --- | --- | --- |
| login/members-only/private/DRM | `PLATFORM_RESTRICTED` | 403 |
| rate limit/429/captcha | `PLATFORM_RATE_LIMITED` | 429 |
| unsupported URL/no extractor | `UNSUPPORTED_PLATFORM` | 422 |
| timeout/connection reset | `PLATFORM_UNAVAILABLE` | 503 |
| 其他 | `PARSE_FAILED` | 422 |

#### Scenario: Rate limit error mapping
- **WHEN** 异常消息包含 "429" 或 "rate limit"
- **THEN** 返回 `AppError` 且 `code` 为 `platform_rate_limited`

#### Scenario: Default parse failure mapping
- **WHEN** 异常消息不匹配任何已知模式
- **THEN** 返回 `AppError` 且 `code` 为 `parse_failed`

### Requirement: to_parse_response conversion
系统 SHALL 提供 `source_info_to_parse_response()` 函数，将 `SourceInfo` 转换为 `ParseResponse`，保持现有 API 契约兼容：

#### Scenario: SourceInfo converts to ParseResponse
- **WHEN** 传入包含 `variants` 和 `platform_profile` 的 `SourceInfo`
- **THEN** 返回的 `ParseResponse` 包含 `formats`（含推荐预设和原始格式）、`source_site`、`platform_id`

#### Scenario: Resolution presets built from variants
- **WHEN** `variants` 包含 height=1080 的视频变体
- **THEN** `ParseResponse.formats` 包含 1080p/720p/480p/360p 预设，1080p 标记为 `available=True`
