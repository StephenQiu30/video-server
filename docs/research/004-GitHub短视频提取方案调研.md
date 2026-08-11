# 004 GitHub 短视频提取方案调研

- 日期：2026-08-11
- 目标：寻找可用于增强本系统抖音、快手等公开视频能力的可维护社区方案
- 边界：只研究公开、非 DRM、用户有权处理的内容；不采用公共解析服务、MITM、账号自动化或客户端签名绕过

## 1. 筛选结论

| 项目 | 许可证/活跃度 | 快手路径 | 结论 |
| --- | --- | --- | --- |
| `yt-dlp/yt-dlp` | Unlicense；仓库固定 commit | 当前 supported sites 无 Kuaishou extractor | 继续作为统一格式、下载和插件宿主；快手需仓库插件 |
| `soimort/you-get` | `LICENSE.txt` 为 MIT；2026-07 仍更新 | extractor 搜索旧页面 `playUrls` | 结构简单但当前页面已变化，不直接复用 |
| `JoeanAmier/KS-Downloader` | GPL-3.0；2026-08-10 更新 | curl_cffi Android impersonation；移动页 `window.INIT_STATE`，支持视频/图集 | 协议事实经独立验证；GPL 源码不复制进 MIT 主仓 |
| `CharlesPikachu/videodl` | PolyForm Noncommercial；2026-08-10 更新 | 桌面 `__APOLLO_STATE__` + 浏览器 fallback，包含每日样本检查 | 证明社区 canary 价值；许可证不适合主仓，不复制 |
| `lulu-ls/video-downloader` | GitHub 标记 MIT，但 LICENSE 仅保留 Electron Boilerplate 版权；最后代码推送 2025-01 | 桌面 `__APOLLO_STATE__` | 许可证归属和维护证据不足，排除代码复用 |
| 无许可证/公共解析 API 项目 | 不明确或闭源中转 | 上传 URL 到第三方解析站 | 全部排除 |

## 2. 独立验证

没有直接运行或嵌入上述项目。使用本仓库固定的 curl-cffi/yt-dlp 环境独立验证：

1. 普通 curl 请求快手桌面详情页可能只得到 63 字节 `result=2` 或 SPA 配置壳。
2. `Chrome-131:Android-14` 请求同一作品的第一方移动分享页可取得 `window.INIT_STATE`。
3. 状态中的 `photo.share_info` 能把页面作品 ID 与返回媒体绑定。
4. `manifest.adaptationSet[].representation[]` 提供 H.264/HEVC HTTPS MP4；`mainMvUrls` 可作单格式 fallback。
5. 真实 CDN 文件经 ffprobe 确认为 MP4，包含视频和 AAC 音频，不是抽帧或图片序列。
6. `v.kuaishou.com` 与 `www.kuaishou.com/f` 短链会跳到快手第一方移动域；过期、审核中内容可能仍能打开页面但没有可播放 `photo`，必须判为链接不可用。

## 3. 采用方式

- 采用：本地 yt-dlp 插件、固定浏览器指纹、第一方分享页、作品身份校验、真实 canary、稳定错误。
- 不采用：社区源码复制、常驻浏览器 fallback、公共解析 API、账号 Cookie、图集截断、DRM 或签名绕过。
- 许可证：新插件为本仓库独立 MIT 实现，不产生新增第三方运行依赖；现有 Provider SBOM 中的 trusted extractor plugins 条目继续覆盖。

## 4. 参考

- [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- [you-get 快手 extractor](https://github.com/soimort/you-get/blob/049548f3f3f35e67ba8d3181c71fdc71d11cf260/src/you_get/extractors/kuaishou.py)
- [you-get MIT license](https://github.com/soimort/you-get/blob/049548f3f3f35e67ba8d3181c71fdc71d11cf260/LICENSE.txt)
- [KS-Downloader](https://github.com/JoeanAmier/KS-Downloader)
- [KS-Downloader HTML extractor](https://github.com/JoeanAmier/KS-Downloader/blob/f1e25a021b46021991d12dd1d81b6b4a2c3e62d7/source/extract/extractor.py)
- [videodl 快手实现](https://github.com/CharlesPikachu/videodl/blob/master/videodl/modules/sources/kuaishou.py)
- [videodl daily canary](https://github.com/CharlesPikachu/videodl/blob/master/scripts/daily_check_videodl.py)
