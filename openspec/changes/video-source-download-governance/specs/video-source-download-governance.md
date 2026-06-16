# video-source-download-governance

## 1. 支持口径定义

### 1.1 支持条件

一个视频源 SHALL 只有同时满足以下全部条件，才算当前项目支持：

1. URL 能通过安全校验和平台画像识别，或被明确允许进入通用公开视频 fallback。
2. `/api/parse` 能返回至少一个可下载 format，且 format 与 Worker 的 `yt-dlp` format selector 兼容。
3. `/api/tasks` 能创建任务并保存用户选择的 `format_id`。
4. Worker 能完成 `yt-dlp.extract_info(..., download=True)` 下载。
5. 下载产物能通过 FFmpeg/FFprobe 校验。
6. 产物能上传到对象存储，并通过预签名链接交付。
7. 对登录、会员、付费、版权、DRM、地区限制、风控和私密内容，MUST 不绕过限制，只返回明确失败语义。

### 1.2 支持状态分类

支持矩阵 MUST 区分以下三种状态：

| 状态 | 含义 | 判定条件 |
| --- | --- | --- |
| `supported_download` | 已有平台画像、可解析、可创建任务、可由 Worker 下载并交付产物 | 满足 §1.1 全部条件，且有下载链路验收证据 |
| `parse_only_or_unverified` | 能解析或能识别，但缺少真实下载验收证据 | 有平台画像和适配器，但无 Worker 下载成功证据 |
| `fallback_attempt` | 未知公网 host，仅通过 `yt-dlp` fallback 尝试 | 无平台画像，仅通过 `YtDlpAdapter` fallback |

### 1.3 禁止行为

1. MUST NOT 把"平台画像命中"等同为"已支持下载平台"。
2. MUST NOT 把"可解析"或"可识别"表述为"正式可下载支持"。
3. MUST NOT 把 fallback 尝试列为正式支持平台。

## 2. 支持矩阵要求

### 2.1 必需字段

支持矩阵文档 MUST 包含以下字段：

| 字段 | 说明 |
| --- | --- |
| `platform_id` | 平台稳定唯一标识 |
| `host` | 支持的主域名 |
| `adapter` | 适配器类名 |
| `download_engine` | 下载引擎（如 `yt-dlp`） |
| `required_auth` | 是否需要认证（`none`、`cookie`、`login`） |
| `known_limits` | 已知限制（公开视频、风控、地区等） |
| `validation_evidence` | 验收证据类型和路径 |
| `support_status` | `supported_download`、`parse_only_or_unverified` 或 `fallback_attempt` |

### 2.2 平台覆盖

支持矩阵 MUST 至少覆盖以下平台画像：

- B 站（`bilibili`）
- 抖音（`douyin`）
- 快手（`kuaishou`）
- 小红书（`xiaohongshu`）
- 西瓜视频（`ixigua`）
- 微博（`weibo`）
- TikTok（`tiktok`）
- X / Twitter（`x`）
- Instagram（`instagram`）
- YouTube（`youtube`）
- Vimeo（`vimeo`）
- Dailymotion（`dailymotion`）
- 未知公网 host（`fallback_attempt`）

## 3. 中心化架构约束

### 3.1 单中心规则

1. 视频源接入的唯一中心 SHALL 是 `app.sources` 下的 adapter、model、registry 与 parse service。
2. `app.services.download_adapter` 中的旧 adapter/registry/response conversion MUST NOT 继续作为并行中心存在。
3. Worker 下载可以继续使用 `yt-dlp`，但下载能力、错误语义和支持矩阵 MUST 与 `app.sources` 的中心化模型对齐。
4. 新增视频源 MUST NOT 通过 router 或 worker 中的 host 分支实现。

### 3.2 验收证据要求

每个 `supported_download` 平台 MUST 至少有：

1. 解析 contract 测试。
2. format selector 到 Worker 下载选项的契约测试。
3. 下载执行 smoke 或可替代的 `yt-dlp` fake integration 测试。
4. 成功产物进入对象存储并生成下载链接的链路验证。
5. 失败语义覆盖：受限内容、风控/429、unsupported、网络异常。

## 4. 失败路径

### 4.1 平台限制

对登录、会员、付费、版权、DRM、地区限制内容：

1. MUST NOT 绕过限制。
2. MUST 返回 `platform_restricted` 错误码。
3. MUST 包含可理解的失败原因。

### 4.2 风控与限流

对平台风控和限流：

1. MUST NOT 重试绕过。
2. MUST 返回 `platform_rate_limited` 错误码。
3. SHOULD 建议用户稍后重试。

### 4.3 不支持的内容

对 `yt-dlp` 无 extractor 或平台限制访问：

1. MUST 返回 `unsupported_platform` 错误码。
2. MUST NOT 声称该平台被支持。

## 5. 验证方式

1. 文档验证：PRD09 必须独立说明"支持=可下载交付"的定义。
2. 代码验证：`app.sources` 必须是唯一中心，旧中心必须被删除或降级。
3. 测试验证：每个 `supported_download` 平台必须有下载链路级测试。
4. 矩阵验证：支持矩阵必须列出每个平台的状态和验收证据。
