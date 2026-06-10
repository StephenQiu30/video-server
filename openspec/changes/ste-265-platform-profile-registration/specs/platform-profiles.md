# Spec: Platform Profiles

## Requirements

### R1: Platform Profile Registry

系统 SHALL 维护一个平台画像注册表，每个画像包含以下字段：
- `id` (str): 平台标识符
- `display_name` (str): 平台展示名称
- `category` (str): 平台分类
- `hosts` (tuple[str, ...]): 平台域名列表
- `compliance_note` (str | None): 合规提示

### R2: Formally Supported Platforms

系统 SHALL 支持以下 5 个正式支持平台：

| platform_id | display_name | category | hosts |
| --- | --- | --- | --- |
| `youtube` | YouTube | overseas-video | youtube.com, youtu.be, youtube-nocookie.com |
| `bilibili` | B 站 | cn-video | bilibili.com, b23.tv |
| `tiktok` | TikTok | overseas-short-video | tiktok.com |
| `x` | X | social-platform | x.com, twitter.com |
| `instagram` | Instagram | social-platform | instagram.com |

### R3: Additional Platforms

系统 MAY 支持以下额外平台（非 PRD02 正式支持）：
- douyin (cn-short-video)
- kuaishou (cn-short-video)
- xiaohongshu (cn-short-video)
- ixigua (cn-short-video)
- weibo (cn-short-video)
- vimeo (overseas-video)
- dailymotion (overseas-video)

### R4: Compliance Notes

- 正式支持平台 MUST 有 compliance_note
- cn-video 和 cn-short-video 平台 MUST 有平台特定的合规提示
- social-platform 平台 MUST 有默认合规提示
- overseas-video 和 overseas-short-video 平台 MAY 使用默认合规提示

### R5: Host Matching

`matches_host` 方法 SHALL 支持：
- 精确匹配（normalized host == item）
- 子域名匹配（normalized host endswith `.item`）

### R6: Platform Recognition

`find_platform_profile(url)` SHALL：
- 从 URL 中提取 hostname
- 遍历 PLATFORM_PROFILES 找到第一个匹配的画像
- 返回 PlatformProfile 或 None

## Scenarios

### Success: X platform recognized
- Input: `https://x.com/user/status/123`
- Expected: profile.id == "x", profile.category == "social-platform"

### Success: Instagram platform recognized
- Input: `https://www.instagram.com/reel/abc`
- Expected: profile.id == "instagram", profile.category == "social-platform"

### Success: YouTube platform recognized
- Input: `https://www.youtube.com/watch?v=abc`
- Expected: profile.id == "youtube", profile.category == "overseas-video"

### Success: Bilibili platform recognized
- Input: `https://www.bilibili.com/video/BV1xx411c7mD`
- Expected: profile.id == "bilibili", profile.category == "cn-video"

### Success: TikTok platform recognized
- Input: `https://www.tiktok.com/@u/video/123`
- Expected: profile.id == "tiktok", profile.category == "overseas-short-video"

### Failure: Unknown host returns None
- Input: `https://example.com/video/123`
- Expected: None
