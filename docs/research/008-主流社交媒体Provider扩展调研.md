# 主流社交媒体 Provider 扩展调研

日期：2026-08-12

## 1. 决策标准

本轮只新增同时满足以下条件的平台入口：

1. 当前固定 yt-dlp commit `5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc` 有专用 extractor，而不是 Generic 猜测。
2. 公开单视频/Clip 样本的 metadata 可解析。
3. 最小完整媒体能够下载，并通过 ffprobe 的视频、音频、时长和容器检查。
4. Provider URL 可以收敛到明确单内容路径，主页、时间线、直播、合集和登录内容可以 fail closed。
5. 不需要把用户链接或 Cookie 发送给公共第三方解析服务。

这继续遵循 [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ) 与 [README](https://github.com/yt-dlp/yt-dlp/blob/master/README.md) 的实践：实际调用验证，不把支持列表当成当前可用性证明；impersonation 只在 Profile 需要时启用。

## 2. 本轮新增支持

| Provider | 首期入口 | 固定 extractor | 完整媒体证据 | 精确边界 |
| --- | --- | --- | --- | --- |
| Snapchat Spotlight | `/spotlight/{id}` | `SnapchatSpotlight` | 583,698 bytes；约 4.64 秒；H.264 + AAC | 不支持 Story、好友内容、账号页和登录内容 |
| LinkedIn | `/posts/...activity...`、`/feed/update/urn:li:activity...` | `LinkedIn` | 3,305,080 bytes；约 161.89 秒；H.264 + AAC | 只支持公开单视频帖子；公司页、Learning、Event 和登录墙不纳入 |
| Telegram | `t.me/{public_channel}/{message_id}` | `TelegramEmbed` | 5,796,200 bytes；约 61.11 秒；H.264 + AAC | 只支持公开频道单视频；私聊、受限频道、频道主页和多资产帖子不纳入 |
| Kick | `/{channel}/clips/{clip_id}` 或等价 `?clip=` | `KickClip` | 51,180,722 bytes；约 44.72 秒；H.264 + AAC | 只支持公开 Clip；直播、VOD、频道主页和订阅内容不纳入 |
| Tumblr | `www.tumblr.com/{blog}/{post_id}` | `Tumblr` | 804,917 bytes；约 7.66 秒；H.264 + AAC | 只支持公开单视频帖子；主页、dashboard、图片和多资产帖子不纳入 |

下载文件仅用于本地兼容性验证，完成 ffprobe 与 SHA-256 后已立即删除。持续生产 canary 仍必须使用项目自有或明确授权、通过 Secret 配置的目标。

## 3. Profile 设计

- 五个平台都使用独立 version、capability、client profile 和 canary suite。
- Snapchat 只声明 `single_video + short_video`。
- Kick 只把公开 Clip 纳入 `single_video + clip_or_vod`，但 URL gate 明确拒绝 live/VOD。
- LinkedIn、Telegram、Tumblr 只声明 `single_video`。
- Tumblr 当前出口需要 Profile 级 Chrome impersonation；其他四个平台保持默认客户端，避免全局伪装。
- Kick 的 `?clip=` 入口规范化到稳定 `/clips/{id}` 入口；额外 query、其他路径和不合法 id 均拒绝。
- Telegram 多资产帖由 yt-dlp 返回 playlist；当前单视频模型不静默选择其中一项，因此最终会 fail closed。
- Snapchat 暴露了 yt-dlp 的标准单表示输出差异：`--dump-single-json` 可能只在顶层返回已选 `format_id`/`url`，而没有 `formats[]`。Runner 现已在统一 metadata 层把该结构归一化为一个候选，再复用既有受控 proxy probe 和语义格式选择；没有增加平台专用 fallback。

## 4. 未新增的平台

| 候选 | 当前证据 | 决策 |
| --- | --- | --- |
| Bluesky | 固定 `Bluesky` extractor 对官方测试向量返回 API HTTP 400 | 保持研究状态，不登记，不落入 verified |
| Rumble | 默认客户端与 Chrome impersonation 均返回 HTTP 403 | 保持研究状态，不通过无限切换指纹绕过 |
| Threads | 当前固定 yt-dlp 无专用 extractor；社区实现混合图片与视频资产 | 等独立单视频插件和多资产领域模型，不交给 Generic |
| Mastodon | 当前固定引擎没有满足项目入口约束的统一专用 extractor；实例域名不可穷举 | 需要类似 PeerTube 的批准实例与 SSRF/DNS 防护设计 |
| Likee/Kwai 国际版 | 现有实现存在媒体 URL 推导或地域/身份边界不稳定 | 继续研究，不复用国内快手 Profile |
| Rumble live、Kick live/VOD、LinkedIn Learning/Event | 超出公开社交单视频范围，可能涉及长时、登录或权益 | 明确不进入本轮 Profile |

## 5. 上游实现依据

- [Snapchat Spotlight extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/snapchat.py)
- [LinkedIn extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/linkedin.py)
- [Telegram Embed extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/telegram.py)
- [Kick extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/kick.py)
- [Tumblr extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/tumblr.py)

## 6. 结论

本轮新增五个严格限定的主流社交媒体 Profile。它们扩大的是公开单视频/Clip 能力，而不是整个平台所有页面的下载承诺。DRM、付费、会员、私密、登录、直播录制、时间线和多资产内容继续拒绝。
