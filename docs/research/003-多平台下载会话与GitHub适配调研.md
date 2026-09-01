# 003 多平台下载会话与 GitHub 适配调研

- 状态：Completed
- 调研日期：2026-08-10
- 范围：当前仓库、固定 yt-dlp 提交、GitHub 上游实现、公开视频平台的会话与请求证明机制
- 结论：保留 yt-dlp + EJS + FFmpeg 主链，把 Cookie 禁令调整为默认关闭、Provider allowlist 下的受控会话能力；优先修复 YouTube 的会话、PO Token、固定出口和错误分类，再按真实 canary 扩展其他平台。

> 2026-08-10 实施更新：本文第 3 节记录的是实施前基线。Profile/context、操作级 Cookie jar、YouTube 运维 Runner、POT sidecar 拓扑、错误映射和 Provider 状态 API/UI 已落地；真实 Cookie/POT E2E、动态 canary 与生产验收状态以 005 Acceptance 为准。

> 2026-08-29 状态说明：第 6 节平台矩阵是调研时快照，不是当前支持清单。视频号现行匿名公开链路与 `degraded` 边界以 015 调研、025 设计/验收为准；腾讯视频当前为 `disabled`，快手当前为 `kuaishou-public`。

> 2026-08-30 YouTube 复核：第 1–5 节中 yt-dlp `2026.07.04` / `5d6b8c8` 和 bgutil `1.3.1` 是调研与故障复现基线，不再是当前运行时。现行锁定版本、PID1 恢复/日志隔离、sidecar 网络、验证结果和部署结论见第 10 节；上述历史表格保留当时证据，不用它们判定当前平台状态。

## 1. 执行摘要

当前 YouTube 失败不是“项目不支持 Shorts”，也不是 yt-dlp 版本过旧或 JavaScript challenge runtime 缺失。仓库固定 commit `5d6b8c8` 的包报告版本为 `2026.07.04`，镜像同时包含 Node 24 和 `yt-dlp-ejs 0.8.0`；用户样本和另一个公开样本都在当前统一出口上返回 `LOGIN_REQUIRED / Sign in to confirm you're not a bot`。这说明当前主要故障是出口信誉或平台访问验证，Cookie 可以成为解决方案的一部分，但不能替代 PO Token、正确 client/EJS 或稳定出口。

源码还有四个放大问题：

1. YouTube 只使用普通 `ProviderProfile`，Runner 的 inspect、下载和 probe 命令都没有会话参数。
2. `provider_access_required` 同时表示 fresh Cookie、YouTube bot challenge 和 Vimeo login，API 又把它固定翻译为“cookie uploads are not supported”，诊断失真。
3. Download Worker 会在真正下载前重新 inspect；当前下载错误映射没有 `provider_*`，因此同一会话失败可能被错误归为可重试 `worker_lost`。
4. Provider Registry 登记了 17 个平台 key，但登记域名、镜像存在 extractor、真实可用、需要会话和当前不支持没有分层。

推荐方案不是在 `/api/inspections` 中直接塞一段 Cookie，也不是开放任意 yt-dlp 参数。第一阶段由运维为 YouTube 配置专用账号的只读 Cookie Secret，Runner 每次操作在独占 tmpfs 创建 `0600` 可写 jar，并在一次下载操作的重解析、双流和 probe 之间串行复用；第二阶段才提供 owner-scoped `ProviderCredential` 资源、Vault/Broker 和显式 `credential_id`。两阶段都不允许 Cookie 进入 URL、数据库明文、outbox、消息、日志、共享 `/work` 或 API 响应。

## 2. 调研方法与版本

1. 按浏览器 → API → application → Media Runner → yt-dlp 的真实调用链检查当前实现和错误映射。
2. 使用仓库固定依赖复核用户样本与公开样本，分别测试当前代理和显式无代理路径。
3. 阅读 yt-dlp 固定提交中的平台 extractor，而不只依据 supported-sites 名单。
4. 阅读 yt-dlp 官方 Wiki、MeTube、cobalt、gallery-dl、bgutil POT Provider 的源码、许可证和部署说明。
5. 将“技术上可认证”与“产品允许处理”分开；Cookie 不改变公开、用户有权、非 DRM 的产品边界。

| 组件 | 本次固定事实 | 用途 |
| --- | --- | --- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp/tree/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc) | 包报告版本 `2026.07.04`；仓库固定 commit `5d6b8c8` | 视频 extractor、格式发现和下载 |
| [yt-dlp EJS](https://github.com/yt-dlp/yt-dlp/wiki/EJS) | 项目锁定 `yt-dlp-ejs 0.8.0`，运行时为 Node 24 | YouTube n/signature challenge |
| [gallery-dl](https://github.com/mikf/gallery-dl/tree/86047cf67a12bdb6ff1085774f8ad9fc347e8da9) | `1.32.9` / `86047cf` | 图片、轮播、用户媒体流候选 |
| [bgutil-ytdlp-pot-provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) | `1.3.1` 调研基线 | YouTube 自动 PO Token Provider 候选 |

## 3. 当前实现与问题定位

### 3.1 调用链

```text
DownloadWorkspace
  → POST /api/inspections
  → InspectMedia
  → MediaRunnerHttpClient
  → POST /internal/v1/inspect
  → MediaRunnerService.inspect
  → MediaCommands.inspect
  → yt-dlp
```

下载任务并不复用最初的媒体直链。`MediaRunnerService.download` 会先重新 inspect，再调用一个或两个 `download_stream`，必要时还会执行 `download_probe_sample`。因此 Cookie、client profile、User-Agent、PO Token 和出口 affinity 必须贯穿：

```text
initial inspect
  = download re-inspect
  = video stream
  = audio stream
  = probe sample
```

只让首页解析携带 Cookie 会产生“解析成功、任务失败”；只让 yt-dlp 携带 Cookie 而让 ffprobe 直接访问受保护媒体 URL，也可能在 probe 阶段失败。

### 3.2 当前缺口

| 位置 | 当前事实 | 影响 |
| --- | --- | --- |
| `runner/provider_registry.py` | Profile 只有 host、固定参数、重试和 URL 规范化 | 不能表达 auth mode、Cookie 域、POT、限流或 canary |
| `runner/provider_catalog.py` | YouTube 是普通 `_standard` profile | 没有 YouTube 专用会话或请求证明策略 |
| `runner/settings.py` | 只有统一/Provider 出口代理 | 没有 Secret 路径、临时目录或会话版本配置 |
| `runner/commands.py` | 三条 yt-dlp 路径都没有 `--cookies` | 会话从未进入真实子进程 |
| `api/schemas/inspections.py` | 请求只有 `url` 且 extra forbid | 直接提交 Cookie 会被 422；该边界应保留 |
| `runner/commands.py` | 多类错误合并为 `provider_access_required` | 无法区分 Cookie、POT、IP、限流和 extractor 回归 |
| `api/errors.py` | detail 固定称 Cookie 上传不支持 | 用户被错误引导，截图即为该结果 |
| `download_execution/errors.py` | 不识别 `provider_*` | 下载前重解析失败会误归为 `worker_lost` 并放大重试 |
| `docker-compose.yml` | Runner 和 Download Worker 共享 `/work` | Cookie 临时文件绝不能放在任务工作区 |

### 3.3 根因分层

| 层次 | 典型信号 | 正确处理 | Cookie 能否单独解决 |
| --- | --- | --- | --- |
| EJS / signature | `nsig`, player JS 或 signature 失败 | 更新 yt-dlp/EJS 和受支持 JS runtime | 不能 |
| 登录会话 | login required、age/account gate、fresh Cookie | 使用 allowlist 下的有效 Cookie；验证账号权益 | 可以处理部分场景 |
| YouTube PO Token | GVS/Player/Subs 403、格式缺失 | 自动 POT Provider，token 与 client/session/video 绑定 | 不能 |
| 出口信誉 | `Sign in to confirm you're not a bot`、IP block | 固定可信出口、降速、冷却；必要时与 Cookie 同出口 | 不保证 |
| 限流 | 429、risk control、重试提示 | Provider/账号/出口限流，尊重 `Retry-After` | 不能 |
| extractor 回归 | 页面/API schema 变化、字段缺失 | 更新固定提交或可信插件，canary 验证 | 不能 |
| 权益或 DRM | premium/private/not entitled/DRM | fail closed，不做规避 | 不能也不应尝试 |

## 4. GitHub 方案对比

| 项目 | 可借鉴能力 | 限制与许可证 | 决策 |
| --- | --- | --- | --- |
| [yt-dlp](https://github.com/yt-dlp/yt-dlp) | 活跃 extractor、EJS、固定 client 参数、Cookie、proxy、重试、FFmpeg 协作 | 参数面很大；必须固定提交和命令模板 | 继续作为视频主引擎 |
| [bgutil POT Provider](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) | 自动生成 YouTube PO Token；HTTP sidecar 适合多进程 | GPL-3.0；上游明确不保证解决 403 或 bot check | 作为显式启用的 YouTube sidecar，先做许可证/SBOM 审查 |
| [MeTube](https://github.com/alexta69/metube) | 上传 Cookie 时限制大小、`0600` 临时文件、原子替换；成熟队列 UX | AGPL-3.0；允许高度可配置 yt-dlp，数据模型不同 | 只借鉴 Secret 文件生命周期，不复制代码 |
| [cobalt](https://github.com/imputnet/cobalt) | 服务级 adapter、Cookie manager、YouTube session server、限流 | AGPL-3.0；YouTube.js 维护面更大，缺抖音/小红书 | 只借鉴能力矩阵和 session coherence，不替换主链 |
| [gallery-dl](https://github.com/mikf/gallery-dl) | Instagram/X/Reddit 等图片、轮播和时间线；Cookie source/update/rotation | GPL-2.0；输出为多媒体集合，与当前单视频模型不同 | 仅作为独立 OCI Runner 的后续候选，不能直接导入核心 |
| [Seal](https://github.com/JunkFood02/Seal) | Android 端 Cookie 与 yt-dlp 集成示例 | GPL-3.0；客户端产品，服务端隔离/并发模型不同 | 不作为服务端实现基线 |

MeTube 的任意 yt-dlp override 和 cobalt 的公共实例都不能直接复制。用户输入的原始 options 可能扩大到命令、文件和网络能力；公共中转又会泄露源 URL、会话并引入不可审计依赖。

## 5. YouTube 专项结论

### 5.1 推荐执行顺序

1. 保持 yt-dlp 默认 YouTube clients，不因旧教程硬编码 Android 或 `all`。
2. 确认 EJS/runtime 健康；本项目当前已满足这一层。
3. 匿名公开内容先走无 Cookie pool。
4. 出现明确登录或 bot challenge 时，在 allowlist 下选择 YouTube 运维会话，并保持 Cookie、client、User-Agent 和出口一致。
5. 对格式缺失或 GVS 403，使用 `mweb` + 自动 GVS PO Token Provider；不保存手工静态 token。
6. 若仍是 IP challenge，停止放大请求，进入出口冷却/治理；不要把真实账号 Cookie 投到已被 block 的高并发出口。

yt-dlp 官方说明 YouTube 会轮换账号 Cookie，使用账号还有临时或永久封禁风险。生产运维 Secret 应使用无个人资产的专用账号、低请求率，并按官方流程从独立私密会话导出：登录后在唯一 tab 打开 `youtube.com/robots.txt`，只导出 YouTube 域 Cookie，随后关闭且不再打开该私密会话。[YouTube Cookie 指南](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies)。这是生产多用户路径；macOS 单机按需来源不要求手工导出，也不应被扩展成生产对个人 Chrome 的依赖。

PO Token 与 Cookie 不是同一个凭据。当前官方 TL;DR 是通过 Provider plugin 为 `mweb` 的 GVS 请求自动提供 token；大量 token 会与视频 ID 或 session 绑定，手工长期缓存已经不推荐。[PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)

### 5.2 安全发布约束

- yt-dlp `--cookies` 会在退出时回写 Cookie jar，不能直接指向只读 Secret mount。
- 每次 Runner 操作从不可变、版本化只读源复制到独占 tmpfs 的唯一 jar，目录 `0700`、文件 `0600`；一次 download RPC 的重解析、双流和 probe 串行复用该 jar，操作结束后 `finally` 删除。
- 当前 `/work` 同时挂载给 Download Worker 和 Runner，禁止在其中创建 Cookie 副本。
- 同一运维账号初始并发为 1；inspect、重解析、双流下载共享统一重试预算。
- 轮换采用 `pending → canary → active → retired`，不按猜测 TTL 盲目定时刷新。
- 运维账号不得持有 Premium、频道会员、购买/租赁或接受 private share；credentialed inspect 必须在下载前只允许不依赖账号权益的 `public/unlisted`，`availability` 未知或受限时 fail closed。

## 6. 平台适配矩阵

下表的“已登记”只表示当前 Registry 能识别域名，不表示实时可用。真实状态必须由受控 canary 得出。

| Provider 族 | 当前基线 | 匿名主链 | 受控会话/Token | 主要风险与目标策略 |
| --- | --- | --- | --- | --- |
| YouTube | 已登记；当前出口 `access_required` | yt-dlp + EJS 默认 clients | 运维 Cookie；mweb GVS POT；固定出口 | P0 修复目标；分开诊断 EJS、Cookie、POT、IP 和 DRM |
| Bilibili | 已登记；公开样本曾 E2E 成功 | yt-dlp UGC；内建 WBI/指纹 | `SESSDATA` 仅在后续明确权益场景评审 | 高画质、番剧、课程、地域与 risk control 不等同解析器失败 |
| 抖音 | 已登记；可信公开分享页插件曾 E2E 成功 | 规范化短链 → share-page plugin → yt-dlp | 新鲜站点 Cookie/动态签名为后续独立 adapter 议题 | Cookie 单独不保证 API 成功；签名失败应报 degraded，不伪报 login |
| TikTok | 已登记；未冻结 canary | yt-dlp + curl-cffi impersonation + web challenge | `sid_tt` 可选；仅 allowlist 会话 | WAF、IP/区域和 private 状态需分离；不无限轮换 device id |
| 小红书 | 已登记；带有效 token 的公开分享链曾 E2E 成功 | 保留 `xsec_token` 的长链/短链 → yt-dlp | 会话后续评审，不自行生成 token | 短链过期、页面 schema、图文笔记和原画缺失分别分类 |
| Vimeo | 已登记；未冻结 canary | player URL + yt-dlp + impersonation | 账号 Cookie/密码是不同机制，默认关闭 | 数据中心 IP/TLS、Referer、密码和私有权益不得合并为 Cookie 错误 |
| X / Twitter | 已登记；未冻结 canary | 单 tweet 用 yt-dlp guest token | `auth_token + ct0` 供后续 owner-scoped 会话 | NSFW/protected 需认证；相册/时间线才考虑 gallery-dl |
| Instagram | 已登记；未冻结 canary | 公开 post/reel 用 yt-dlp + impersonation | `sessionid` 供后续专用/owner-scoped 会话 | 匿名频控、Cookie 失效、private/follow-only 分离；carousel 需多媒体模型 |
| Facebook | 已登记；未冻结 canary | 公开 video/reel 用 yt-dlp | 登录墙场景的 Cookie 后续评审 | Relay/GraphQL/Tahoe schema 与 CDN chunk 403 不能一律归为 login |
| Twitch | 已登记；未冻结 canary | 公开 clip/VOD 用 yt-dlp 动态 playback token | `auth-token` 只代表账号，仍需内容权益 | 直播录制仍在产品范围外；subscriber-only 无权益则终止 |
| Reddit | 已登记；未冻结 canary | yt-dlp guest/loid；v.redd.it HLS/DASH | `reddit_session` 仅对获准 private/quarantine 场景评审 | processing 可延迟重试；gallery/profile 属多媒体扩展 |
| Pinterest / 微博 | 已登记；未冻结 canary | yt-dlp public/guest 流程 | 默认关闭运维账号 | 先建 metadata + Range canary，再决定专用 Profile |
| 优酷 / 腾讯视频 | 已登记；未冻结 canary | yt-dlp 公开免费内容 | 登录/会员不在首期 | 地域、付费、DRM fail closed；格式稀疏继续受 probe 限制 |
| Dailymotion / NicoNico | 产品范围排除 | 无 | 无 | 域名 fail closed，不进入 Generic |
| Generic | 未知站点 fallback | 仅公开 direct media/HLS/DASH/embed | 永远不授予 Provider Cookie | redirect 后必须重新归类；不得成为万能签名/验证绕过器 |
| 视频号 / 快手 | 当前没有受支持 extractor/Profile | 无 | 无 | 明确 `unsupported`；不使用 MITM、公共 Worker 或第三方解析 API |

## 7. 引擎边界

- 视频单条、音视频分离流和 remux：继续使用 yt-dlp + FFmpeg/ffprobe。
- 图片、轮播、用户时间线：只有在领域模型支持一个帖子多个条目后，才评估独立 gallery-dl Runner。
- gallery-dl Runner 与视频 Runner 分池，固定 extractor 配置、输出 manifest 和配额，不共享 Cookie 文件或任意命令参数。
- Generic fallback 不携带会话；短链重定向到已知 Provider 后重新执行 URL 安全校验和 Profile 选择。
- 检测到 DRM、会员/购买权益不足或用户无权访问时直接终止，不将“可传 Cookie”解释为授权。

## 8. 推荐落地优先级

1. 修正错误 taxonomy 和 download-stage 映射，停止把会话问题归为 `worker_lost`。
2. 建立 `ProviderAccessContext`，先在无 Cookie 路径验证 inspect/download 一致性。
3. 落地 YouTube 运维 Cookie Secret、Runner 独占 tmpfs、单账号低并发和固定出口。
4. 增加可选 POT sidecar，并分别测试 Cookie、POT、IP challenge 和 sidecar 故障。
5. 建 Provider capability/canary/status，回归 Bilibili、抖音、小红书并验证 Tier 2 平台。
6. 再设计用户 `ProviderCredential`、Vault/Broker 和 gallery-dl 多媒体模型。

详细目标设计、需求、实施和验收分别见 `docs/design/005-多平台Provider策略设计.md`、`docs/prd/005-多平台Provider与会话适配需求.md`、`docs/plans/005-多平台Provider与会话适配计划.md` 和 `docs/acceptance/005-多平台Provider与会话适配验收.md`。

## 9. 权威参考

- [yt-dlp supported sites](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md)
- [yt-dlp YouTube extractor / Cookie guidance](https://github.com/yt-dlp/yt-dlp/wiki/Extractors#youtube)
- [yt-dlp PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide)
- [yt-dlp EJS Guide](https://github.com/yt-dlp/yt-dlp/wiki/EJS)
- [yt-dlp FAQ：Cookie、IP 与 User-Agent](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)
- [固定提交：Bilibili extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/bilibili.py)
- [固定提交：Douyin/TikTok extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/tiktok.py)
- [固定提交：小红书 extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/xiaohongshu.py)
- [固定提交：X/Twitter extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/twitter.py)
- [固定提交：Instagram extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/instagram.py)
- [固定提交：Facebook extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/facebook.py)
- [固定提交：Vimeo extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/vimeo.py)
- [固定提交：Twitch extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/twitch.py)
- [固定提交：Reddit extractor](https://github.com/yt-dlp/yt-dlp/blob/5d6b8c8cd19785c3086ae3a9ec618c45e25eb3bc/yt_dlp/extractor/reddit.py)
- [MeTube Cookie 文件实现](https://github.com/alexta69/metube/blob/master/app/main.py#L1034-L1065)
- [cobalt API environment / YouTube session](https://github.com/imputnet/cobalt/blob/main/docs/api-env-variables.md)
- [gallery-dl authentication](https://github.com/mikf/gallery-dl/blob/master/README.rst#authentication)
- [gallery-dl supported sites](https://github.com/mikf/gallery-dl/blob/86047cf67a12bdb6ff1085774f8ad9fc347e8da9/docs/supportedsites.md)
- [gallery-dl GPL-2.0 License](https://github.com/mikf/gallery-dl/blob/master/LICENSE)

外部平台和反滥用机制会持续变化；该研究应在 yt-dlp 提交、POT Provider、平台 Cookie 语义或产品授权范围变化时复核。

## 10. 2026-08-30 YouTube 上游复核与落地结论

### 10.1 固定运行时

| 组件 | 现行固定事实 | 运行门禁 |
| --- | --- | --- |
| [yt-dlp 2026.08.19](https://github.com/yt-dlp/yt-dlp/releases/tag/2026.08.19) | CLI 版本 `2026.08.19`，package metadata `2026.8.19`，commit [`3a08beaf031ab68f966401ead017ac81fe8486cf`](https://github.com/yt-dlp/yt-dlp/commit/3a08beaf031ab68f966401ead017ac81fe8486cf) | readiness 同时比对 package metadata 版本和 `direct_url.json` 的锁定源，避免同版本名的未审计来源漂移 |
| [bgutil-ytdlp-pot-provider 1.3.2](https://github.com/Brainicism/bgutil-ytdlp-pot-provider/releases/tag/1.3.2) | Python 插件 `1.3.2`；sidecar `brainicism/bgutil-ytdlp-pot-provider:1.3.2@sha256:9a96e6385ce1928da87dea07b1cab0413d2cf8c07a3b8a8bd419f53df2c3843c` | Runner readiness 只比对插件版本；sidecar 不参与 API/公共 Runner readiness 或 Compose health wait gate，由版本库托管的 PID1 supervisor 在 `/ping` 连续 3 次失败后重启上游子进程 |
| EJS / JavaScript runtime | `yt-dlp-ejs 0.8.0` + Node 24 | 继续处理 n/signature challenge，不用浏览器页面代替受控 Runner |
| YouTube Profile | `youtube-v5`，`youtube:player_client=mweb`，attestation `bgutil-mweb-player-gvs` | 公开链路在服务端自动 mint 任务期 POT，不接收用户 Cookie/PO Token/任意 yt-dlp 参数；yt-dlp/inspection 均为单次 |

版本选择不是只追随最新 tag：bgutil `1.3.2` 包含 [YouTube A/B 变体修复](https://github.com/Brainicism/bgutil-ytdlp-pot-provider/commit/495a47f)；yt-dlp 上游则已因持续 403 [移除 `android_vr` 无 POT 降级](https://github.com/yt-dlp/yt-dlp/commit/dae52d8386557f4c19ab58a9ae56062b8d52b3af)。因此当前 Profile 不恢复 Android/VR/TV 等旧 client 教程，也不使用 `player_client=all`。

Supervisor 以 `stdio: "ignore"` 完全丢弃上游子进程 stdout/stderr，因为上游会输出 minted token 及其绑定标识；持久容器日志只留 supervisor 的固定、无密故障事件。Sidecar 只加入 internal `youtube_pot_net`，Runner 的 `runner_egress_net` 同样为 internal；默认拓扑只有 Squid 加入非 internal `proxy_uplink_net`。Runner 与 sidecar supervisor 从同一 `RUNNER_EGRESS_PROXY` / `RUNNER_PROVIDER_EGRESS_PROXIES` 配置解析实际路由；非法 JSON/URL 失败关闭且不输出代理地址，bgutil `/get_pot` 请求体内的 yt-dlp `request_proxy` 优先于环境回退，保证 token mint 与媒体下载使用同一实际代理。专用出口必须是加入 `youtube_pot_net` 的受管双网卡 gateway，映射使用其内部服务地址，不能指向任意公网 proxy hostname。

### 10.2 POT 与 IP challenge 的边界

yt-dlp 官方 [PO Token Guide](https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide) 将 PO Token 定位为 Player/GVS/Subs 请求证明；[bgutil 项目](https://github.com/Brainicism/bgutil-ytdlp-pot-provider) 也不承诺绕过 403 或 bot check。因此：

- 能生成有效 POT 只证明请求证明组件正常，不证明当前出口 IP 被 YouTube 信任。
- 已返回 `LOGIN_REQUIRED` / `Sign in to confirm you're not a bot` 的 IP 不能由 POT 修复；这类失败应归类为 `egress_challenged`，而不是 `pot_required`。
- 本轮在固定新运行时后，某些公开视频可完成 metadata，但多个可用于安全验收的公开授权样本在当前共享出口仍被 bot challenge。单个 metadata 成功不能替代授权样本的完整 media E2E，平台状态不得因此恢复 `verified`。

### 10.3 面向 C 端的长期方案

`RUNNER_PROVIDER_EGRESS_PROXIES={}` 时，YouTube 实际仍通过共享 `default` egress；Profile 的 `egress_pool` 是期望路由，不是已经获得专用 IP 的证据。Runner 使用实际代理 URL 的 SHA-256 前 12 位指纹生成非 Secret `egress_affinity_id`，带 `default` 或 `provider:youtube` scope；URL 变更即创建新 context。本轮将缺失 Runner context 的 canary 出口记为 `unresolved`，防止平台状态伪报已使用 `youtube-sticky`。

平台状态通过 HMAC/replay 防护的批量 Runner 接口读取实时 context，并只聚合精确相同的 SHA-256 generation；generation 覆盖 provider、profile、access mode、credential version、实际 egress affinity、client profile、attestation/POT version 和 engine commit。旧 generation 保留审计但即使晚完成也不能影响当前状态；scheduler 同样按该 generation 查询最近执行时间。某个 runner group 取不到或返回畸形 context 时，只将该组平台标为 `degraded`，不会用历史 cohort 猜测当前运行时。`chrome-default` 是动态本机来源标识，不是 Cookie 内容哈希；与它关联的近期真实下载成功只证明该来源在相同非敏感上下文完成过制品，不是“当前 Cookie cohort 已验证”，也不能单独将 `access_required` 提升为 `verified`。

面向多用户的长期可用性要求部署方为 `youtube` 配置自身运维、稳定、合规且可审计的专用出口，在同一实际 affinity 上完成 metadata + media canary，并以低并发、`Retry-After` 和冷却控制请求。这是部署能力门禁，不是需要再增加解析器补丁。

当前 Runner 已把 yt-dlp retry 作为 Profile 策略；YouTube 的三个 yt-dlp retry scope 均为 `0` 且 inspection 只执行一次。429 与 `egress_challenged` 不在相同 context 中立即重试，yt-dlp warning 保留并优先识别复合 429。该收敛只停止本地请求放大，不等同于健康出口；`Retry-After`、跨层持久化总预算和按 context generation 的 cooldown 仍须在生产门禁中完成。

macOS 单机按需助手在 Chrome Cookies 数据库的 SQL 查询阶段就只选择 `youtube.com` / `youtube-nocookie.com` 域，仅解密并输出该查询的行。每次读取在独立进程组中执行，有 15 秒硬超时；超时、取消或异常都终止并回收整个进程组。它不启动或操作 Chrome，不是常驻后台服务，也不是宿主机平行应用入口；项目启动仍只使用根 Docker Compose。生产多用户服务不安装该助手，不依赖个人 Chrome。

不采用下列降级：

- 不启动或操控宿主 Chrome，不查询、解密或输出非 YouTube 域 Cookie。macOS 单机模式仅在用户显式安装按需助手后，按 YouTube Operator 操作同步 Chrome Default；生产多用户服务不依赖个人浏览器。
- 不接入免费/公共代理列表、WARP/Tor 或高频 IP 轮换；它们不能提供可审计、可持续的 C 端服务质量。
- 不把用户 URL 交给公共 cobalt/Invidious/其他解析 Worker，不用它们绕过当前 Runner 的出网、隐私和权益边界。
- 不将 [yt-dlp-getpot-wpc](https://github.com/coletdjnz/yt-dlp-getpot-wpc) 这类启动真实浏览器的实验性 POT 方案并入服务端默认链路；它不解决 IP 信誉，且与无后台 Chrome 的隐私要求冲突。
