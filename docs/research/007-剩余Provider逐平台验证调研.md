# 剩余 Provider 逐平台验证调研

日期：2026-08-12

## 1. 验证原则

本轮不以 yt-dlp 的“支持站点列表”或 extractor 存在作为可用证据，而是固定项目引擎 commit `5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc`，逐个平台执行以下检查：

1. 使用 `--ignore-config`、`--no-playlist`、固定插件目录和 Node.js EJS runtime 执行 metadata。
2. 只为 Profile 明确声明需要的 Provider 启用浏览器 impersonation，不全局强制伪装。
3. metadata 通过后，使用 Runner 的真实格式选择和下载语义完成媒体下载。
4. 用 ffprobe 校验时长和音视频轨道，并计算 SHA-256；临时媒体随后立即删除。
5. 需要账号、Cookie 或不同出口的失败保持 `access_required`，extractor/页面协议回归保持 `degraded`，不通过无界重试或 Generic fallback 伪造支持。

该方法遵循 [yt-dlp 官方 FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ) 的建议：站点是否可用必须实际调用 yt-dlp 验证；cookies、User-Agent 与请求出口需要保持一致；Cloudflare 场景需要新鲜 cookie 和匹配的浏览器指纹。[官方 README](https://github.com/yt-dlp/yt-dlp/blob/master/README.md) 同时指出 impersonation 不应无条件启用，因为强制启用可能降低速度和稳定性。[支持站点列表](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md?plain=1) 也明确不构成每个 URL 当前可下载的证明。

## 2. 逐平台结果

| Provider | metadata | 真实媒体/语义 | 当前状态 | 精确边界 |
| --- | --- | --- | --- | --- |
| YouTube | 失败：bot/sign-in challenge | 未进入媒体阶段 | `access_required` | 保持受控运维会话、同出口和 POT 路径；当前匿名出口不得标记 verified |
| TikTok | 失败：`Unexpected response from webpage request` | 未进入媒体阶段 | `degraded` | 当前固定引擎的网页 extractor 回归；不通过盲目切换 impersonation 绕过 |
| Facebook | 通过 | Runner metadata 通过；媒体最近 5 次 4 成功、最近 4 次连续成功；成功样本约 10 秒且含音视频轨道 | `verified` | 仅公开 Reel/单视频与单视频分享帖；图片、多附件继续 fail closed |
| Twitch | 通过 | 约 32 秒，音视频轨道通过 | `verified` | 公开 Clip；不承诺订阅、登录或受限 VOD |
| Reddit | 失败：`Account authentication is required` | 未进入媒体阶段 | `access_required` | 当前匿名访问不可用；不把登录态浏览器 Cookie 扩散到匿名 Runner |
| Pinterest | 通过 | 约 58 秒，音视频轨道通过 | `verified` | 公开单视频 Pin；图片 Pin、相册不在本 Profile 能力内 |
| 微博 | 通过 | 约 918 秒，720p MP4 音视频轨道通过 | `verified` | 公开单视频；`scrubber_hd` JPEG 预览格式被格式选择器排除 |
| 优酷 | 通过 | 约 702 秒，音视频轨道通过 | `verified` | 公开单视频；会员、付费、地域限制不在已验证范围 |
| 腾讯视频 | 历史媒体探针通过；024 重新判定不满足权益/接口门禁 | 约 216 秒，音视频轨道通过 | 运行时仍为 `verified`；要求 `unknown/disabled` | 历史样本只能证明当时取得媒体；未公开 `cKey` 机制和缺少 `public_free` 正向证据，不能作为当前生产批准；024 Phase 0 降级未实施，属于发布阻断 |

Facebook、Twitch、Pinterest、微博、优酷和腾讯视频的 metadata 与 media 结果已通过 `ProviderCanaryService` 写入本地 `provider_canary_results`。结果表只记录 target id、Provider/Profile、阶段、耗时、结果和固定引擎引用，不保存完整目标 URL。

YouTube 的结果也符合 yt-dlp [已知问题 #3766](https://github.com/yt-dlp/yt-dlp/issues/3766) 对 bot challenge 的说明：被限制的出口不能靠反复注入 Cookie 根治，盲目使用个人账号 Cookie 还会增加账号风险。Facebook 当前上游仍有公开的 [`Cannot parse data` 问题 #15161](https://github.com/yt-dlp/yt-dlp/issues/15161)，因此项目只对已验证的公开 Reel/单视频 Profile 作有限承诺，并保留稳定错误分类。

## 3. yt-dlp 推荐实践在项目中的落地

- Provider Profile 明确保存 version、capability、access mode、client profile 和 canary suite；状态页只展示这个受证据约束的范围。
- Facebook 使用 Profile 级 Chrome impersonation；其他已通过平台保持默认客户端，避免全局强制 impersonation。
- `--no-playlist` 与产品“单视频”领域模型保持一致；图片、相册、播放列表和多资产输入均 fail closed。
- Cookie 只允许从项目批准的受控 Secret 注入，并要求同 User-Agent、同出口、同 operation context；不会直接读取用户日常浏览器的全站 Cookie。
- metadata 成功不是发布证明；媒体必须经过 Runner 格式选择、实际下载、ffprobe 与 hash。
- 上游 `_TESTS` 地址只用于本次固定引擎兼容性诊断，下载文件已删除。生产持续探针仍必须使用项目自有或明确授权、经 Secret 配置的目标。

## 4. 特殊问题

微博 extractor 同时返回 JPEG scrubber 预览和真实 MP4。直接使用 yt-dlp 默认“最优格式”可能选中图片预览，因此本项目不能把 yt-dlp CLI 的退出码等同于视频成功。本轮新增回归测试，确保图片格式不会进入视频下载选项；实际 Runner 选择到 720p/1080p MP4。

腾讯视频样本顶层 metadata 没有稳定时长，但媒体流可用。Runner 通过已选媒体流的 probe 补全为约 216 秒，证明最终合同应以语义化 Runner 输出为准，而不是依赖 extractor 的单一顶层字段。

## 5. 结论

本轮在 2026-08-12 历史上新增六个严格限定的匿名公开单视频/Clip Profile；024 复核后只有 Facebook、Twitch、Pinterest、微博和优酷的这批证据继续有效。腾讯视频当前代码仍错误地保留 `verified`，必须先降为 `unknown/disabled`；YouTube 与 Reddit 保持 `access_required`，TikTok 标记为 `degraded`。这不是对平台全部内容类型的承诺，也不改变 DRM、付费、会员、私密、地域限制和多资产内容的拒绝策略。
