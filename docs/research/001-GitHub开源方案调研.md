# GitHub 开源方案调研

- 调研日期：2026-08-06
- 结论：采用“成熟底层工具 + 自有安全编排与产品领域层”，不直接 fork 一体化下载站。

## 候选方案

| 项目 | 可复用能力 | 结论 |
| --- | --- | --- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 活跃的站点 extractor、格式探测与下载；支持 Python 嵌入和 CLI | 采用，但只在无业务凭据的 Media Runner 子进程中运行；固定版本并持续跟进安全发布 |
| [yt-dlp sample plugins](https://github.com/yt-dlp/yt-dlp-sample-plugins) | 官方 `yt_dlp_plugins.extractor` 扩展结构与加载约定 | 采用其插件边界，在 Runner 镜像内随项目交付可信站点适配器，不开放用户插件目录 |
| [MeTube](https://github.com/alexta69/metube) | yt-dlp Web UI、队列、并发与自托管经验 | 仅借鉴产品流程；其本地文件/状态和高度可配置 yt-dlp 模式不符合本项目的 PostgreSQL 事实源、对象存储、AI 分析与严格 Runner 边界 |
| [cobalt](https://github.com/imputnet/cobalt) | 轻量粘贴即下载体验、服务适配器和限流思路 | 仅借鉴交互；AGPL-3.0、代理式交付和服务专用逻辑不作为本项目代码基线 |
| [lux](https://github.com/iawia002/lux) | Go 下载库、清晰度枚举和 FFmpeg 合并 | 不采用；最近可见 release 为 2024，当前 extractor 维护速度不如 yt-dlp，且切换 Go 会增加双技术栈成本 |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) | 本地 CTranslate2 Whisper 转录、时间戳 segment | 作为可选本地 ASR adapter；默认部署不强绑模型或 GPU |
| [OpenAI Python](https://github.com/openai/openai-python) | 官方异步客户端、Responses API 与类型定义 | 作为首个托管 AI adapter；密钥只进入 AI Worker，并保持 provider port 可替换 |
| [markmap](https://github.com/markmap/markmap) | Markdown/树结构思维导图渲染 | 前端渲染候选；后端只保存带 transcript evidence 的中立 JSON tree，避免绑定渲染库格式 |

## 为什么不直接 fork 下载站

现成项目能快速完成“输入 URL、拿到文件”，但本产品还要求语义清晰度计划、下载前重解析、任务 lease/outbox、对象存储、匿名资源隔离、AI 证据链和思维导图。直接 fork 会让这些能力依附于原项目的队列、文件系统和 API 约定，长期演进成本更高。

因此本项目只复用成熟且边界清晰的能力：yt-dlp 负责 extractor，FFmpeg/ffprobe 负责媒体处理与验证，ASR/LLM 通过 adapter 接入；任务、权限、安全和产品契约由本仓库拥有。

## MediaTrack 兼容方案

截至 2026-08-06，按 `mediatrack.cn`、审片 URL 和 yt-dlp extractor 在 GitHub 精确检索，只找到 [LinkHelper](https://github.com/oneNorth7/LinkHelper) 一类浏览器嗅探脚本，没有可直接复用且持续维护的 MediaTrack 服务端提取器。通用嗅探脚本依赖浏览器页面状态，也无法满足 Runner 的无 Cookie、固定参数和出网隔离边界，因此不引入项目。

本项目改用 yt-dlp 官方插件机制实现最小站点适配：只匹配 `app.mediatrack.cn/reviews/{review}/{asset}`，调用站点公开链接 API 获取短时 token，只接受 API 明确标记 `has_rights=true` 的 `mediatrack.cn` HTTPS 播放转码，并在每次下载前重新解析签名 HLS。插件不读取浏览器 Cookie、不接受账号凭据、不请求被页面禁用的原文件下载接口；最终制品继续经过现有大小/时长限制、FFmpeg remux 和 ffprobe 校验。

## 抖音链接兼容边界

Runner 会将抖音精选页的 `modal_id`、`/share/video/{id}` 和抖音短链交给 yt-dlp 的抖音 extractor，并对抖音请求使用独立的浏览器指纹和有限重试。当前抖音网页接口会要求新鲜浏览器会话（`Fresh cookies ... are needed`），这属于平台反爬验证；本项目不上传 Cookie、不生成平台签名，也不绕过验证。因此当前实现保证分享链接能够进入正确的 extractor，并返回明确的“需要平台访问会话”错误，但不宣称在无浏览器会话时完成所有抖音视频下载。

## 主流平台策略注册表

Runner 使用 `ProviderStrategy + ProviderRegistry + GenericFallback`：平台策略只管理域名别名、规范化 URL、固定请求参数和有限重试；下载、格式选择、FFmpeg 校验仍走同一条流水线。当前登记并经过 extractor 清单核验的平台包括 YouTube、哔哩哔哩、抖音、TikTok、Vimeo、X/Twitter、Instagram、Facebook、Twitch、Reddit、Pinterest、微博、优酷、腾讯视频、Dailymotion 和 NicoNico。未登记但被 yt-dlp 支持的 HTTP(S) 地址仍交给 Generic extractor；平台目录不等于可用性保证，yt-dlp 官方也明确说明站点规则会变化，最终必须以实际解析结果为准。[Supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)

当前镜像中的 yt-dlp extractor 清单未包含快手，因此快手仅保留域名识别，不宣称已具备下载能力；只有在 extractor 可用并通过实际解析测试后，才会将其升级为正式平台。

## 关键风险与治理

1. yt-dlp 的 2026 发布记录包含命令注入、危险文件类型和外部 downloader 相关安全修复，因此不能把任意参数透传给用户，也不能启用 `--exec`、`--netrc-cmd`、aria2c 或 cookie 上传。
2. 站点规则会变化。数据库保存语义下载计划，Worker 开工前重新 inspect；provider format id 只作短期 hint。
3. “入口 URL 校验”不能阻止 DNS rebinding 或重定向 SSRF。Runner 必须处于无默认出网的内部网络，并只通过拒绝私网地址的 egress proxy 访问公网。
4. AI adapter 必须输出 schema 化 JSON，并由应用层验证所有章节、观点和导图节点引用真实 transcript segment；模型原始输出不直接成为产品事实。

## 推荐基线

- Web/API：React + FastAPI，同源单镜像。
- 状态与异步：PostgreSQL + transactional outbox + RabbitMQ。
- 下载：隔离 Media Runner + yt-dlp + FFmpeg/ffprobe。
- 制品：私有 MinIO bucket + 短时签名 URL。
- AI：独立 AI Job/Worker；托管 provider 优先，可选 faster-whisper 本地 ASR。
- 导图：中立 JSON tree + evidence ids，前端按需接 markmap 或自定义渲染。

## 2026-08-07 真实来源回归与后续方案

使用浏览器从 `http://127.0.0.1:8002` 执行解析、格式选择、服务端下载、完整性校验和文件获取，得到以下边界：

| 来源 | 真实样本结果 | 当前处理 |
| --- | --- | --- |
| Bilibili | 解析成功，360p MP4 下载并通过完整性校验 | 保持 yt-dlp 主链路 |
| 小红书 | 带有效 `xsec_token` 的完整分享链接解析、下载、校验成功；无 token 的旧直链失败 | 接受完整公开分享链接；后续补短链规范化与 token 缺失提示 |
| YouTube | 当前 egress IP 被要求 `Sign in to confirm you're not a bot` | 映射为 `provider_access_required`，不再返回泛化 502 |
| 抖音 | 当前网页接口要求 fresh browser session | 继续返回 `provider_access_required`，不上传 Cookie |
| 视频号 | 公开分享页可访问，但当前 yt-dlp/Generic 无法提取 | 不宣称支持；返回不可用结果，不接入 Cookie 或公共中转服务 |

GitHub 调研后的取舍：

1. yt-dlp 官方 [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) 推荐为 YouTube `mweb` 客户端配置 PO Token Provider。[bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) 提供独立 HTTP 服务和 yt-dlp 插件，但官方仓库也明确说明它不保证绕过 403 或 bot check。该方案会新增常驻服务、插件供应链和 GPL-3.0 合规评估，因此只作为显式启用的部署选项候选，不在默认 Runner 中静默引入。
2. 小红书专项实现和公开 issue 均显示新版分享链依赖 `xsec_token`；例如 [XHS-Downloader #261](https://github.com/JoeanAmier/XHS-Downloader/issues/261) 记录了 `/m/` 短链跳转到带 token 长链的变化。后续应在 Runner 内受控跟随短链并保留最终公开 URL，而不是自行生成平台签名。
3. [wx_channels_download](https://github.com/ltaoo/wx_channels_download) 的服务端分享链接解析需要元宝 Cookie，或将链接交给 Cloudflare Worker；另一条路线是本机 MITM/证书注入。两者分别违反当前“Runner 无业务凭据/不把源链接发送给第三方”和“服务端不安装抓包根证书”的边界，因此不纳入当前服务。

优化顺序：

1. 为已登记 Provider 增加定时真实 canary，记录 `last_verified_at`、错误分类和 extractor 版本；外部站点波动不得阻断普通 PR CI。
2. 前端展示“已验证 / 需要平台验证 / 当前不支持”，不要把 extractor 清单或“1000+”等同于下载保证。
3. 监控按 Provider、错误码和 yt-dlp 版本聚合，区分反机器人验证、链接过期、解析器回归、下载失败和对象存储交付失败。
4. 本地对象存储预签名地址必须与宿主机实际监听地址一致；Windows/Docker Desktop 默认使用 `127.0.0.1`，避免 `localhost` 优先解析到未监听的 IPv6 回环地址。
