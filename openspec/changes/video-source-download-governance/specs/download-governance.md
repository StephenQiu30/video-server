# Spec: 视频源下载治理

## 支持状态定义

### supported_download
- 平台可以通过 `app.sources` 适配器解析
- 可以创建下载任务
- Worker 可以执行下载并交付产物
- 有自动化测试或 fake integration 证据

### parse_only_or_unverified
- 平台可以通过 `app.sources` 适配器解析
- 可以创建下载任务
- 但 Worker 下载未验证或可能失败（平台限制、风控等）
- 不能承诺绕过平台限制

### fallback_attempt
- 未知公网 host
- 安全 host 校验通过
- 使用 yt-dlp 通用 fallback
- 不保证下载成功

## 中心化架构约束

1. 视频源选择只能从 `app.sources` 进入
2. 不允许保留并行 registry
3. `app.services.download_adapter` 不再定义独立 adapter/registry 中心
4. 所有平台支持判断必须基于 `app.sources` 适配器

## 支持矩阵字段

| 字段 | 说明 |
| --- | --- |
| platform_id | 平台标识符 |
| host | 平台域名 |
| adapter | 使用的适配器类名 |
| download_engine | 下载引擎（yt-dlp 等） |
| required_auth | 是否需要认证 |
| known_limits | 已知限制 |
| validation_evidence | 验证证据（测试名或文档） |
| support_status | supported_download / parse_only_or_unverified / fallback_attempt |

## 下载链路验证

1. parse -> task -> worker download -> object storage delivery
2. format_id 传递契约：TaskCreate.format_id -> Worker YoutubeDL({"format": ...})
3. 推荐格式：`bestvideo+bestaudio/best`
4. 分辨率格式：`bv*[height<=720]+ba/b[height<=720]`

## 失败分类

1. 缺少 FFmpeg -> media_tools_missing
2. 缺少 yt-dlp -> download_failed
3. 平台限制 -> platform_restricted
4. 429/风控 -> platform_rate_limited
5. unsupported URL -> unsupported_platform
6. 下载后无产物 -> download_failed
