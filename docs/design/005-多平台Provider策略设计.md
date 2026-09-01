# 005 多平台 Provider 与会话适配设计

- 状态：Partially Implemented；production verification pending
- 日期：2026-08-10
- 最近更新：2026-08-30
- 前置调研：`docs/research/003-多平台下载会话与GitHub适配调研.md`
- 实现状态：Phase 1 已落地版本化 Profile、非 Secret 访问上下文、匿名/YouTube 运维 Runner 路由、操作级 Cookie jar、权益防火墙、服务端托管 POT sidecar、稳定错误、Provider 探针结果表/定时执行器/动态状态聚合、`GET /api/providers` 与前端状态页。YouTube 已停止 yt-dlp 与 Runner 的同出口立即重试放大；授权目标的真实 Cookie/POT canary、完整视频 Agent E2E、账号权益漂移自动停用，以及遵守 `Retry-After` 的跨层总预算/cooldown 仍是生产发布门禁；Phase 2 的用户 Credential Broker/Vault 与 gallery-dl 尚未实现。

> 当前实现增量（2026-08-30）：Runner 固定 yt-dlp package `2026.8.19`（CLI 输出 `2026.08.19`）/ commit `3a08beaf031ab68f966401ead017ac81fe8486cf`，YouTube Profile 为 `youtube-v5`，匿名公开链路由服务端自动使用 `mweb` + EJS + bgutil POT Provider `1.3.2`。Sidecar 锁定为 `brainicism/bgutil-ytdlp-pot-provider:1.3.2@sha256:9a96e6385ce1928da87dea07b1cab0413d2cf8c07a3b8a8bd419f53df2c3843c`；Runner 与 sidecar 只接 internal 网络，只有 Squid 接入非 internal 的 `proxy_uplink_net`。默认 HTTP(S) proxy 是 Squid；配置 YouTube 专用代理时，部署方必须把受管双网卡网关加入 internal `youtube_pot_net`，映射只能指向它的内部服务地址，bgutil 与 yt-dlp 使用同一实际 proxy。用户无需上传 Cookie、PO Token 或 yt-dlp 参数；生产 Compose 默认不读取个人浏览器会话，但获批准的单机 production Compose 可通过与本机相同的 `launchd QueueDirectories` 按需助手读取 Chrome Default。Chrome Cookies 数据库的 SQL 查询只选择 YouTube 域，单次读取使用 15 秒硬超时的独立进程组，超时或取消时整组回收；它只在 YouTube Operator 操作开始时运行，排空后退出且不启动 Chrome。该助手不是平行应用入口，项目仍仅通过根 Docker Compose 运行。YouTube Profile 只执行一次 inspection，三个 yt-dlp retry scope 均为 `0`；429 和出口 challenge 不在 Runner 内立即重试，warning 保留用于稳定分类。POT 只解决 Player/GVS 请求证明，不能修复已被 `LOGIN_REQUIRED` / bot challenge 的出口 IP；YouTube 在面向 C 端的生产环境恢复 `verified` 前，部署方必须配置可持续、合规、由自身运维的 YouTube 专用出口并通过授权样本 media canary，不使用公共代理、WARP/Tor 或公共解析服务作为可用性基础。

## 1. 目标

在不改变语义下载计划、任务租约、FFmpeg 校验和对象存储交付的前提下，把现有“域名识别 + 固定参数”升级为版本化 Provider 控制面和隔离执行面：

1. 默认匿名访问公开内容；只有 allowlist Provider 和明确策略可以使用受控会话。
2. YouTube 支持运维管理的 Cookie、自动 PO Token 和固定出口，分别诊断登录、请求证明和 IP challenge。
3. inspect、下载前重解析、视频流、音频流与 probe 始终使用同一个访问上下文。
4. 用真实 canary 表达平台能力，不把 registered host 或 extractor 清单写成成功承诺。
5. 为后续 owner-scoped ProviderCredential 和图片/轮播引擎保留边界，但不把凭据或任意命令带入业务消息。

## 2. 非目标

- 不绕过 DRM、会员/购买权益、private/follow-only 权限或平台地域限制。
- 不自动化账号密码、验证码、2FA、设备注册或账号养号。
- 不在 inspection/download JSON 中直接上传 Cookie、Authorization、PO Token 或原始浏览器 profile。
- 不开放任意 yt-dlp/gallery-dl 参数、输出模板、插件、外部 downloader、shell 或文件路径。
- 不把用户 URL 或凭据发送到公共解析 API、公共 Worker 或公共 cobalt 实例。
- 不启动或操控宿主 Chrome，不自动化登录，不读取非 YouTube 域 Cookie，也不把公共代理、WARP/Tor 或个人 Cookie 当作多用户生产服务的稳定出口；本机按需助手是用户显式安装的单机边界。
- 中心服务和 Provider Runner 不通过高频代理轮换、伪造平台签名或安装 MITM 根证书规避访问控制。用户设备 Edge Agent 按 019 的独立产品路径实施，不纳入本编号的 Cookie Runner。
- 不在本编号中开放直播录制、无限播放列表、频道归档或多媒体帖子下载。

Cookie 的一刀切禁令被调整为“默认关闭、Provider allowlist、生命周期受控”的会话能力；本设计中的 Cookie 会话仍只处理用户有权使用且可正向证明为公开、非 DRM 的内容。平台保护内容只有在官方授权 Provider/Connector 按资产明确返回下载/导出授权且输出未加密时才可生成 Artifact；019 Edge Agent 只传输用户已经合法取得并显式选择的 clear 文件，不能访问平台会话或处理受保护媒体。两条路径都不能复用 Cookie 会话扩大权益。

## 3. 当前基线与根因

### 3.1 实施前基线

- `ProviderRegistry` 根据标准化 hostname 选择 18 个 Provider key 或 Generic fallback。
- `ProviderProfile` 可提供 URL 规范化、固定命令参数、检查重试和 Provider 专用出口。
- 仓库固定 yt-dlp commit `5d6b8c8`，该包报告版本 `2026.07.04`；镜像包含 EJS、Node 24、curl-cffi、FFmpeg 和 ffprobe。
- Bilibili、抖音公开分享页和带有效 token 的小红书样本曾完成真实解析/下载验证。
- Runner 只经拒绝私网的 egress proxy 出网，下载前会重新 inspect。

### 3.2 已修复缺陷

- Profile v2 已增加 capability、access mode、Cookie 域、client、attestation、egress、并发、状态和 canary suite；稳定错误仍由共享 classifier 管理。
- YouTube 运维 Runner 的 inspect、download stream 和 probe sample 统一使用操作级 `--cookies`，匿名、Generic 与非 YouTube 路径不携带 Cookie。
- YouTube bot challenge、credential、POT、rate、geo、private/entitlement、DRM 与 extractor regression 已分层；download re-inspect 的 Provider 错误不再降为 `worker_lost`。
- Provider Profile 直接声明 yt-dlp retry 次数；YouTube 的 yt-dlp/inspection 都只尝试一次，429 与出口 challenge 交给上层冷却，不在相同 context 内立即重打。yt-dlp warning 不再被隐藏，复合 `429 + unavailable` 优先归为限流。
- Cookie 源按不可变版本只读挂载，临时 jar 位于 Runner 独占 `/run/provider-secrets-tmp`，不位于共享 `/work`。
- inspection 冻结 `ProviderAccessContextRef` 并随下载快照传递；匿名与运维 Runner 物理分离，YouTube 可选择固定 Provider 出口和内部 POT sidecar。
- Runner readiness 已校验 yt-dlp 包版本与锁定源 commit、bgutil 插件版本。Sidecar 不参与 API/公共 Runner readiness，也不作为 Compose `service_healthy` wait gate；版本库内脚本以只读方式挂载为容器 PID1 supervisor，独立检查 `/ping`，连续 3 次失败才终止并重启上游子进程。上游子进程 stdout/stderr 全部丢弃，防止它输出的 PO Token 或绑定标识进入持久容器日志；supervisor 只记录不含异常原文和证明数据的固定故障事件。YouTube 命令在 spawn 前和失败后执行 2 秒、禁用环境代理/重定向、精确版本的语义预检，因此 sidecar 运行中断裂不会被误归因为出口 challenge；非 YouTube 命令不执行该探测。

### 3.3 仍待生产验收

- 当前环境未配置 YouTube 专用出口时，`RUNNER_PROVIDER_EGRESS_PROXIES={}` 会让实际路由回退到共享 `default` egress；Profile 中的目标 pool 名不能作为实际 affinity 成功证据。Runner 根据实际代理 URL 生成非 Secret 的 SHA-256 前 12 位指纹，例如 `default:<fingerprint>` 或 `provider:youtube:<fingerprint>`；代理 URL 变更即产生新 affinity 和新 context。没有上下文的失败 canary 记为 `unresolved`，不伪报已使用专用出口。
- 当前共享出口对多个公开授权样本返回 bot challenge；在专用出口完成 metadata + media canary 前，平台状态不得标记为 `verified`。
- 尚未提供生产专用账号和授权样本，因此未执行真实 Cookie/POT 的完整 Runner → Worker → MinIO E2E。
- `GET /api/providers` 已合并配置/历史基线与最近 5 条持久化探针结果；定时 metadata/media 执行、连续失败阈值、恢复迟滞和动态降级已实现。真实授权目标默认未配置，能力/Agent E2E gate、指标和自动 kill switch 仍待补齐。
- 账号最小权益使用启动 attestation 和媒体 metadata fail-closed；自动检测账号权益漂移并 disable version 尚未实现。
- 凭据并发当前由单运维 Runner 的 `RUNNER_MAX_ACTIVE_TASKS=1` 和本地 semaphore 约束；跨副本分布式租约尚未实现。
- 429 `Retry-After`、跨 Worker/Runner/yt-dlp 的持久化总预算、POT 刷新一次和出口 cooldown 尚未实现；Runner 内的 429/challenge 与 YouTube yt-dlp 立即重试放大已停止。
- Generic 仍依赖 yt-dlp 内部重定向；“跨 Provider redirect 后重新 admission/context”尚未完成独立控制面实现。

因此 YouTube 修复不是一个布尔值 `cookies_enabled`，而是访问上下文、Secret 生命周期、权益防火墙、请求证明和出口策略的组合；当前实现提供了受控路径，但生产状态必须由真实 canary 决定。

## 4. 设计原则

1. **匿名优先**：公开内容先使用无凭据 Runner；会话不是默认请求头。
2. **显式选择**：access mode 由 Profile 和任务选择决定，不在错误后无界尝试所有账号/clients。
3. **最小授权**：Provider Secret 只进入对应 Provider 的 credentialed Runner，Generic 永远无凭据。
4. **上下文一致**：Cookie、client/UA、visitor/session、POT 和 egress affinity 构成不可拆分的 `ProviderAccessContext`。
5. **业务面无 Secret**：DB、outbox、RabbitMQ、MinIO、日志、trace 和普通 Runner RPC 只保存非 Secret 引用。
6. **失败关闭**：DRM、权益不足、跨 Provider redirect、会话不匹配和未知签名失败不静默降级。
7. **可验证支持**：Provider 状态由 capability + auth mode + region/egress + engine version 的 canary 计算。
8. **固定执行面**：引擎参数由可信 Profile 生成，用户不能透传原始 options。

## 5. 架构

下图同时包含当前 Phase 1 与 Phase 2 目标。当前已经实现 Anonymous Runner、YouTube Operator Runner、Runner-only tmpfs、POT sidecar、非 Secret context 路由和动态 canary 控制面；`User Credential Runner`/Broker 仍是未实现目标。

```mermaid
flowchart LR
    B["Browser / Admin"] --> API["API"]
    API --> CP["Provider Control Plane"]
    API --> DB[("PostgreSQL metadata")]
    W["Download Worker"] --> CP
    CP --> A["Anonymous Runner Pool"]
    CP --> O["Operator Credential Runner"]
    CP --> U["User Credential Runner (Phase 2)"]
    O --> BR["Credential Broker / readonly Secret"]
    U --> BR
    O --> TMP["Runner-only tmpfs"]
    U --> TMP
    O --> POT["YouTube POT Sidecar"]
    A --> E["Provider Egress Gateway"]
    O --> E
    U --> E
    POT --> E
    E --> P["Public media providers"]
```

`youtube-pot-provider` 只加入 internal `youtube_pot_net`；Runner 使用的 `runner_egress_net` 也为 internal。Squid 同时加入这两个内部网络，且是默认拓扑里唯一加入非 internal `proxy_uplink_net` 的服务，因此 Runner/POT 无法绕过代理直连公网。Runner 与 sidecar supervisor 读取同一份 `RUNNER_EGRESS_PROXY` / `RUNNER_PROVIDER_EGRESS_PROXIES` 版本化配置；supervisor 使用与 Runner 一致的无凭据 HTTP(S) URL 规则解析 `youtube` override，非法 JSON/URL 直接拒绝启动，并只把选中的 `HTTP_PROXY` / `HTTPS_PROXY` 传给上游子进程，不传递原始映射。固定版本的 bgutil 插件还会在每次 `/get_pot` 请求体中传递 yt-dlp 当前的 `request_proxy`，sidecar 以该值优先，从而保证 token mint 与媒体请求使用同一实际代理。专用出口必须由部署方以受管双网卡 gateway 加入 `youtube_pot_net`，映射指向该 gateway 的内部地址；不得直接填写任意公网代理 hostname。API 不加入 `youtube_pot_net`，sidecar 不加入 `runner_egress_net`/`proxy_uplink_net` 且不发布宿主端口。

### 5.1 Provider Control Plane

目标控制面负责：

- 解析 URL 后选择版本化 Profile；redirect 改变 Provider 时重新分类。
- 根据 capability、access mode、账号状态、出口状态和配额选择 Runner pool。
- 生成不含 Secret 的 `ProviderAccessContextRef`。
- 聚合 canary、错误、引擎版本和 kill switch，向 API 提供粗粒度状态。

控制面不执行 yt-dlp，不接收 Cookie 原文，也不把凭据放入 outbox。

### 5.2 Runner pools

| Pool | 可见 Secret | 用途 | 网络范围 |
| --- | --- | --- | --- |
| `anonymous-runner` | 无 | 默认公开内容和 Generic | Profile 允许的公共媒体域 |
| `youtube-operator-runner` | 只读 YouTube Secret 源；任务期 POT | 第一阶段 YouTube 会话 | YouTube/Google 媒体域和本地 POT sidecar |
| `user-auth-runner` | 单 owner、单 Provider、短租约 | 第二阶段用户凭据 | 租约声明的 Provider 域 |
| `gallery-runner` | Profile 决定，默认无 | 后续图片/轮播 manifest | 与视频池隔离 |

所有 pool 都保持非 root、只读 rootfs、`no-new-privileges`、无 Docker socket、无 DB/MQ/MinIO/AI 凭据，并只能经 egress gateway 出网。

## 6. Provider Profile v2

现有 Profile 扩展为版本化、静态审计的描述，不从用户请求构造命令参数。

### 6.0 当前代码结构与扩展模式

平台执行面采用组合而非平台子类继承：

1. **Strategy**：`ProviderProfile` 组合 URL normalizer、固定参数、运行时参数、重试和能力策略。
2. **Registry / Factory**：`ProviderRegistry.prepare()` 校验唯一 key/host，并把一次 URL 解析冻结为 `ProviderRequest`；同一操作不再反复按 URL 猜平台。
3. **Builder**：`YtDlpCommandBuilder` 统一生成 inspect、正式下载和 probe sample 命令，通用执行器不包含 YouTube/TikTok 平台分支。
4. **Chain of Responsibility**：有序 `FailureRule` 先匹配通用安全错误，再匹配 Provider marker，输出稳定错误码。
5. **Template Pipeline**：`RunnerInspectionPipeline` 固定执行重试、权益校验、稀疏 metadata 补全和格式归一化；`MediaRunnerService` 只编排工作区、会话、下载、remux 和验证。

```mermaid
flowchart LR
    U["安全 URL"] --> R["ProviderRegistry.prepare"]
    R --> Q["ProviderRequest"]
    Q --> S["Session / Access Context"]
    Q --> I["RunnerInspectionPipeline"]
    I --> B["YtDlpCommandBuilder"]
    B --> P["受限子进程"]
    P --> F["FailureRule chain"]
    I --> O["语义格式选项"]
    O --> D["重解析 / 下载 / remux / ffprobe"]
```

新增接入分三类：

- yt-dlp 已有 extractor 的公开单视频：新增一个 Profile、URL/错误契约测试和匿名 metadata/media canary，不修改命令执行器。
- 需要 URL 规范化或固定 extractor args：在 Profile 组合纯 normalizer/runtime-args 策略，用户输入仍不能产生任意参数。
- yt-dlp 无 extractor：按官方 `yt_dlp_plugins.extractor` 机制增加仓库可信插件及独立 fixture 测试，再登记 Profile；多条目、直播、DRM 或新权益边界必须先扩展领域模型，不能伪装成单视频平台。

```text
key / version / display_name / hosts / engine
url_normalizer / redirect_policy
media_kinds / capabilities
access_modes / credential_precedence
cookie_domain_allowlist / client_profile / impersonation
attestation_policy / egress_pool / sticky_scope
inspect_concurrency / download_concurrency / credential_concurrency
retry_budget / cooldown / timeout
stable_error_mapping / canary_suite
engine_version / plugin_version / license
```

### 6.1 Capability

最小 capability 集合：

- `single_video`
- `short_video`
- `clip_or_vod`
- `audio_video_split`
- `subtitles`
- `image_or_carousel`
- `live`
- `playlist`

只有 `single_video`、`short_video`、`clip_or_vod` 和现有语义格式在当前产品范围。其他能力可以被识别，但在对应领域模型和验收完成前返回 `capability_not_enabled`。

### 6.2 Access modes

| Mode | 当前阶段 | 语义 |
| --- | --- | --- |
| `anonymous` | 已有 | 无 Provider Secret，所有平台默认首选 |
| `operator_managed` | Phase 1 | 运维专用账号，仅为 allowlist Provider 和公开/用户有权内容提供会话 |
| `user_managed` | Phase 2 | owner 创建独立 Credential 资源并显式引用，不跨 owner 共享 |
| `user_device` | 019 待实施 | 用户自有设备本地执行平台 Adapter，只向服务端导入已验证制品；不进入任何 Runner pool |

Profile 的 precedence 是白名单，不是自动穷举。例如 YouTube 可配置 `anonymous → operator_managed`；用户显式选择 `user_managed` 后不自动切换到运维账号，反之亦然。

## 7. ProviderAccessContext

一次 inspection 成功时冻结以下非 Secret 元数据：

```text
provider_key
profile_version
access_mode
credential_version_id
egress_affinity_id
client_profile_id
attestation_provider_version
engine_commit
```

规则：

1. 下载任务保存上述引用，不保存 Cookie、visitor data 或 token 原文。
2. 生产静态凭据的“同一 context”表示同一个不可变 credential snapshot version、client 和出口身份，不要求把初次 inspection 中收到的临时 `Set-Cookie` 持久化到业务数据面。`chrome-default-v1` 是本机动态来源协议标识，不是 Cookie 内容快照 ID；inspect 和 download 各自在操作开始时从同一本机来源刷新。
3. 初次 inspection 与异步 download 各创建一个操作级可写 jar；download 必须先用原 snapshot version 重新 inspect，再让 video/audio stream、probe sample 和需要远程访问的 ffprobe 串行复用该 jar。
4. Download Worker 重解析时必须获得原来源引用；生产静态 snapshot 至少保留到 inspection TTL 和最大排队窗口结束，本机 `chrome-default-v1` 则重新触发同一来源协议。对应来源不可用时返回稳定错误，不用其他账号或匿名模式替代。
5. POT 由同一 client/session/出口上的 Provider 按视频生成；不把 video-bound token 长期持久化。
6. `egress_affinity_id` 不使用 Profile pool 名或代理明文；它由实际代理 URL 的 SHA-256 前 12 位和 `default` / `provider:{key}` scope 组成。URL 变更即视为不同出口，必须新建 context 且旧 canary 不得继续作为当前证据。
7. redirect 到另一 Provider 时销毁 context，重新执行 URL 安全校验和 admission；原凭据不得随 redirect 发送。
8. Profile/credential 已被撤销或版本不一致时，排队任务不再启动；运行中任务按撤销策略终止。

## 8. Secret 与 Cookie 生命周期

### 8.1 第一阶段：运维 Secret

- 只配置 Secret 文件路径，不把 Cookie 内容写入环境变量。
- 源文件按不可变 version 挂载到 credentialed Runner 的 `/run/provider-secrets/{provider}/{version}.cookies.txt:ro`。
- Runner 启动和轮换 canary 验证：普通文件、非 symlink、Netscape header、最大 1 MiB、仅允许该 Profile 的域名。
- 每次 Runner inspect/download 操作在独占 tmpfs `/run/provider-secrets-tmp` 创建唯一目录；目录 `0700`、Cookie jar `0600`。
- 不能把只读源直接传给 yt-dlp，因为 yt-dlp 退出时会回写 Cookie jar。
- 初次 inspection 使用独立 jar 并在返回时销毁；异步 download 从原 snapshot version 新建 jar，重解析、视频流、音频流和 probe 串行复用，让该操作内的 `Set-Cookie` 更新可见。
- 同一 jar 不得被多个子进程并发写；未来若并发下载 stream，必须先增加 Cookie coordinator 或在冻结更新后分叉副本。
- 成功、失败、超时、取消、SIGTERM 和子进程异常都在 `finally` 删除 jar；Runner/container 销毁后 tmpfs 清空。
- 临时文件绝不位于当前 Runner 与 Download Worker 共享的 `/work`。
- 操作级 jar 的更新在终态丢弃，不反向写 Secret；轮换只走运维渠道。

运维 Cookie 版本状态为：

```text
pending → canary → active → retired
                    ↘ rejected
```

新版本只有 canary 通过后才能激活；旧版本至少保留到引用它的 inspection TTL 和最大排队窗口结束，并可在短时窗口回滚。会话出现明确 rotated/expired 信号时标记 `needs_refresh`，不依据猜测 TTL 自动登录或自动化 2FA。

### 8.2 macOS 单机按需来源

- 只有当前登录的 macOS 用户显式安装助手并启用 YouTube Operator 后，解析/下载操作才可触发 Chrome Default 来源；生产多用户服务默认不使用该来源，但获批准的单机 production Compose 可以复用该宿主机来源。
- Chrome Cookies 数据库的 SQL 查询在选择阶段就限制为 `youtube.com` / `youtube-nocookie.com`，只返回并解密中选行；非 YouTube 域 Cookie 不进入 helper 的查询结果、输出文件或日志。
- 单次读取在独立进程组中执行，持有 15 秒硬超时；成功后立即退出，超时、取消或异常时终止并回收整个进程组。helper 不启动、操作或持有 Chrome，不使用定时轮询或常驻端口。
- `chrome-default-v1` 表示动态本机来源协议，不是 Cookie 原文哈希或内容 cohort。其平台状态历史只能证明该来源在相同非敏感上下文近期完成过制品，不证明当前 Cookie 未轮换或仍可用，不能单独将 `access_required` 提升为 `verified`。
- 应用服务的启动与重启仍只使用根 Docker Compose；按需 helper 是凭据适配器，不是宿主机平行应用或新的启动脚本。

### 8.3 第二阶段：用户 ProviderCredential

用户凭据只能通过独立、认证、CSRF 防护的 multipart API 创建：

- 文件限 1 MiB，只接受 Netscape Cookie，解析后剔除非目标域 Cookie。
- 原文使用 KMS/envelope encryption 存放在独立 Vault；PostgreSQL 只保存 owner、Provider、版本、状态、时间和密文引用。
- API 只返回 `credential_id`、Provider、状态、创建/最后验证时间；Cookie 永不可回读。
- Runner 通过 Broker 获得一次性短租约，不由 API/Worker 解密，不经过 RabbitMQ。
- owner A 引用 owner B 的 credential 返回 404，并且不能调用 Runner。
- 撤销后 60 秒内停止新租约并终止仍使用该凭据的进程。

`POST /api/inspections` 继续拒绝 `{cookie: ...}`；Phase 2 只增加可选 `credential_id`。这条约束防止 Secret 混入普通 JSON、访问日志、错误快照和幂等存储，并不等同于禁止 Cookie 功能。

### 8.4 内容权益防火墙

共享运维会话只能解除公开视频的反机器人访问验证，不能把账号自身权益借给用户：

- 专用账号不得订阅 Premium、加入频道会员、购买/租赁内容或接受 private share，也不得保存个人邮件、播放列表和支付资产。
- credentialed inspect 在生成格式前必须校验标准化 `availability` 和 Provider 权益字段；YouTube 第一阶段只允许 `public` 或不依赖账号权益的 `unlisted`。
- `private`、`premium_only`、`subscriber_only`、`needs_auth`、付费/会员标记、`has_drm=true` 和未知 `availability` 都 fail closed。
- download re-inspect 必须重复权益校验，任何媒体字节下载和对象交付都发生在校验通过之后。
- 下载重试请求只创建新的持久化队列任务，不同步依赖 Provider 校验；Worker 执行前必须重新 inspect，来源身份、权益、格式和最终制品完整性校验仍不可绕过。
- Profile 后续启用其他 Provider 会话时必须定义等价的 entitlement classifier；没有可靠证据就不得使用共享运维会话。
- Canary 检测到账号新增权益或 classifier 变为 unknown 时立即 disable 该 credential version。

## 9. YouTube 策略

### 9.1 处理阶梯

1. 公开链接默认由匿名 Runner 自动使用 `mweb` + EJS + bgutil POT Provider，不读取宿主浏览器，不向 C 端用户索取 Cookie 或 PO Token。
2. POT 仅解决 Player/GVS 请求证明；`LOGIN_REQUIRED` / `Sign in to confirm you're not a bot` 按 `egress_challenged` 处理，不通过切 client、重启 Chrome 或轮换个人 Cookie 放大请求。
3. 明确 `credential_required` 且符合 allowlist/权益防火墙时才选择运维会话；会话不能作为出口信誉的修复手段。
4. POT、Cookie、client 和 egress affinity 必须在同一 context；sidecar 获取 token 时沿用同一 proxy/source binding。
5. IP challenge 仍存在时进入冷却并标记实际出口，专用出口 canary 恢复前保持 `degraded` / `blocked`。

不硬编码旧教程中的 Android、iOS、TV 或 `player_client=all`。当前上游会改变各 client 的 POT、Cookie、SABR 和 DRM 行为，Profile 只在受控 canary 证明需要时启用 fallback。

### 9.2 并发与重试

- 每个 YouTube credential subject 初始最多 1 个 active job。
- 匿名 Provider 全局初始 1–2 个 active job；fragment 并发单独限制。
- 视频间随机延时、429/403 指数退避与 jitter 由统一预算控制。
- yt-dlp、Runner、Worker 的重试合计不得相乘；凭据失效、DRM、权益、geo 和 extractor unsupported 不重试。
- Cookie/POT/出口任一变化都创建新 context，不沿用旧格式 URL。

### 9.3 面向 C 端的长期运行门禁

- `RUNNER_PROVIDER_EGRESS_PROXIES` 为 `youtube` 显式映射部署方自己运维的内部出口网关；未配置时的共享 `default` 路由只是安全回退，不构成 YouTube 生产可用性承诺。
- 专用出口要求长期稳定的合规来源、可审计变更、低并发和冷却策略；禁止抓取公共代理列表、自动轮换匿名出口或使用用户个人网络/浏览器会话填补服务端缺口。
- Runner readiness 只证明固定执行依赖健康；POT sidecar 由 PID1 supervisor 内部以 `/ping` 连续失败阈值管理子进程，不参与 API/公共 Runner readiness 或 Compose health wait gate。YouTube 命令自己的语义预检负责快速失败和精确归因。平台可用性必须由同一实际出口上的授权 metadata/media canary 证明。Sidecar 故障只降级 YouTube，API、其他 Provider 和 AI 分析不因该单平台依赖失败而不可用。

## 10. 其他平台策略

| Provider 族 | 主路径 | 会话策略 | 当前产品决策 |
| --- | --- | --- | --- |
| Bilibili | yt-dlp 公开 UGC | anonymous；`SESSDATA` 默认关闭 | 保持已验证公开链；会员/课程/DRM 终止 |
| 抖音 | URL 规范化 + 可信 share-page plugin | anonymous 优先；动态签名 adapter 另审 | 保留公开 fallback；不伪造“Cookie 必然可修复” |
| TikTok | 第一方嵌入 Player item API | anonymous only；无 Cookie/浏览器/device id | canonical video/embed；短链目标重校验；无格式稳定失败 |
| 小红书 | 保留完整 `xsec_token`/短链 + yt-dlp | anonymous；会话后续评审 | 不生成 token；图文笔记不静默当视频 |
| X / Instagram / Facebook | 单视频用 yt-dlp | user-managed 优先于共享运维账号 | 登录墙、NSFW/private、频控和 schema 分开报错 |
| Vimeo | player URL + impersonation | Cookie、password、Referer 分开建模 | private/password 内容不因 Cookie 开放而自动允许 |
| Twitch / Reddit | yt-dlp 公开 clip/VOD/post | 权益 Cookie 后续评审 | live/私有/quarantine 不在首期 |
| Pinterest / 微博 / 优酷 | yt-dlp 公开单视频 | anonymous | 保留当前版本化公开 Profile；受保护或多资产内容 fail closed |
| QQVideo | 仅保留识别用 `qqvideo-public-video-v1` Profile | 无可用访问模式 | `disabled`；历史媒体证据不能恢复下载，重新开放须先满足 024 的官方授权与权益边界 |
| AcFun / Rutube / VK Clips / Dailymotion / NicoNico | 无 | 无 | 不在产品范围；主域及子域 fail closed，不进入 Generic |
| Generic | 公开 direct/HLS/DASH/embed | 永不携带 Provider Secret | redirect 后重新归类 |
| 快手 | 仓库可信 `KuaishouPublicIE` + 第一方移动分享页 | anonymous | `kuaishou-public-v1` 已完成真实 metadata/media 回归 |
| 视频号 | 第一方预览页 + `get_feed_info` 的仓库内可审计 extractor | anonymous only；无 Cookie/浏览器/第三方中转 | `wechat-channels-public-v2` 为 `degraded`；仅处理 `/sph/` 直接公开 clear 媒体，受保护或未公开媒体 fail closed |

图片、carousel、gallery 和用户时间线若进入产品范围，使用独立 gallery-dl engine adapter，返回受限 manifest；在领域模型支持多条目之前不静默只取第一项。gallery-dl 为 GPL-2.0，必须以独立进程/镜像评估分发义务，不直接导入当前核心源码。

## 11. 错误模型

内部错误比公开错误更细；两层都必须保留 `stage`、`retryable`、`retry_after`、`user_action` 和 `operator_action`，但公开响应不暴露账号、Cookie 版本、POT 或出口地址。

| 内部码 | 默认重试 | 处理 |
| --- | --- | --- |
| `credential_required` | 否 | 选择/配置受控会话 |
| `credential_expired` | 否 | 标记 needs_refresh，轮换后新建任务 |
| `credential_rejected` / `credential_revoked` | 否 | 停止使用，不匿名偷降级 |
| `client_context_mismatch` | 否 | 丢弃格式 URL，重新 inspect |
| `pot_required` | 否 | 启用允许的自动 Provider |
| `pot_provider_unavailable` | 短时 | 基础设施退避，不换手工 token |
| `pot_rejected` | 一次刷新 | 同 context 重新 mint 一次 |
| `egress_challenged` | 冷却后 | 隔离出口、降速、通知运维 |
| `provider_rate_limited` | 是 | 遵守 `Retry-After` 和统一预算 |
| `provider_geo_restricted` | 否 | 明确不可用，不规避 |
| `provider_link_unavailable` / `content_deleted` | 否 | 提示复制新的公开分享链或内容已删除 |
| `content_private` / `content_not_entitled` | 否 | 按产品边界拒绝 |
| `drm_protected` | 否 | 永久拒绝 |
| `extractor_regression` | 否 | 降级 Provider，触发工程 canary |
| `media_url_expired` | 一次重检 | 使用原 context 重新 inspect |
| `fragment_failed` | 有界 | 固定次数重试，不能变更 credential |

公开层收敛为稳定、可行动的码：

| 公开码 | 内部原因示例 | 用户动作 |
| --- | --- | --- |
| `provider_auth_required` | `credential_required` | 选择已批准会话或稍后重试 |
| `provider_session_expired` | `credential_expired/rejected/revoked` | 刷新或重新选择凭据 |
| `provider_verification_failed` | POT、EJS、egress challenge | 等待平台恢复；不要求反复上传 Cookie |
| `provider_rate_limited` | Provider/credential/egress 限流 | 按 `Retry-After` 等待 |
| `provider_geo_restricted` | 地域限制 | 当前地区不可用，不提供规避指引 |
| `provider_link_unavailable` | 链接失效、内容删除 | 复制新的公开分享链接或确认内容仍存在 |
| `provider_content_restricted` | private、未获权益 | 检查访问权利；不建议反复更换凭据 |
| `provider_drm_protected` | DRM | 不支持处理 |
| `provider_temporarily_unavailable` | extractor regression、sidecar/Provider degraded | 稍后重试并由运维处理 |

`provider_content_restricted` 只聚合 private/未获权益，不包含链接失效或删除。inspect 和 download 使用同一映射；旧 `provider_access_required` 已删除，未知 `provider_*` 也不再降为 `worker_lost`。

## 12. API 与前端

### 12.1 Phase 1

- `POST /api/inspections` 请求仍为 `{url}`；是否允许 operator session 是部署/Profile 决策。
- `GET /api/providers` 返回 Provider、capability、粗粒度状态、最近验证时间和合法用户动作。
- 错误 detail 不再宣称 Cookie 永远不支持；根据稳定码显示“需要平台会话”“会话已失效”“出口正在验证”“请求证明不可用”等。
- 管理端只展示会话 Provider、版本、状态、最后 canary、启用/撤销；不回显 Secret。
- `GET/POST /api/admin/providers` 与 `PATCH/DELETE /api/admin/providers/{provider_key}` 由管理员维护独立的平台目录。目录表只保存名称、排序和可见性，应用层再与不可由前端修改的 Profile/Canary 基线合并；自定义 key 固定映射为 `unsupported`，不能借目录写入扩大 Runner admission。
- `GET /api/providers` 只返回目录中公开条目并采用管理员名称与排序。目录删除使用逻辑删除，schema seed 仅补充从未出现过的默认 key，不复活已删除条目。

### 12.2 Phase 2

- `POST /api/provider-credentials`：multipart 创建 allowlist Credential。
- `GET /api/provider-credentials`：列出当前 owner 元数据。
- `DELETE /api/provider-credentials/{id}`：撤销，幂等且跨 owner 返回 404。
- `POST /api/inspections` 增加可选 `credential_id`，但永远不接受 Cookie 原文。

OpenAPI 仍是前后端唯一契约；新增接口使用稳定 operationId，前端只通过生成服务调用。

## 13. Capability、Canary 与状态

目标状态聚合维度：

```text
provider + capability + access_mode + egress_region + client_profile + engine_version
```

公开状态：

```text
unknown | verified | degraded | access_required | rate_limited | blocked | disabled | unsupported
```

目标 Canary：

- 匿名 metadata canary：每 6 小时。
- 运维会话 metadata canary：每 6 小时。
- 小文件 Range/完整下载 + remux + ffprobe + SHA canary：每天。
- 每个目标显式声明唯一 `access_mode`；公开矩阵只执行 anonymous，operator
  目标使用独立 `target_id` 单独配置和持久化。
- Canary Runner 不使用业务的 anonymous→operator fallback，失败新鲜度和
  成功证据始终归属实际执行的单一路由。
- 只使用项目自有或明确授权样本，不使用用户 URL/Cookie。
- 记录 Provider、capability、access mode、Profile/engine/POT 版本、egress affinity 引用、阶段、耗时和稳定错误；不记录完整 URL 或 Secret。

最近 5 次至少 4 次成功、最近 2 次连续成功、metadata 成功不超过 6 小时且 media 成功不超过 26 小时，已批准基线才可恢复 `verified`；至少 2 次失败进入 `degraded`；连续 3 次同类永久失败进入 `blocked`。会话失效立即进入 `access_required`。API 已实现该聚合器，但新平台的 `unknown/access_required` 基线不能被下载探针自动提升，必须先完成完整视频 Agent E2E 并显式批准。当前逐平台状态只由 Registry、状态 API 与对应验收文档维护，不在本通用策略中复制易过期快照；微信视频号当前边界见 025，腾讯视频授权媒体边界见 024。

API 通过 HMAC/replay 防护的批量 Runner context 接口读取当前运行时，2 秒内一次解析全部匿名平台，各 operator group 并行且故障隔离。状态和 scheduler 使用完整 context 的 SHA-256 generation：`provider_key + profile_version + access_mode + credential_version_id + egress_affinity_id + client_profile_id + attestation_provider_version + engine_commit`。任一字段变化都会创建新 generation；查询必须在 SQL 排序/限额前按当前 generation 过滤，历史任务即使晚完成也不能污染当前状态或推迟新一轮 canary。无法取得或无法通过语义校验的 group 只将对应平台标为 `degraded`，绝不从历史记录推断“当前 cohort”。动态本机来源 `chrome-default-v1` 不将 Cookie 原文或哈希加入 generation，因此其关联的真实下载只是“这个来源近期成功”的历史证据，不是当前 Cookie 内容 cohort 的验证结果；它不能单独把 `access_required` 提升为 `verified`。

## 14. 可观测性与审计

- 低基数指标按 provider、capability、access_mode、stage、public_error、engine_version 聚合。
- 禁止 URL、query、credential id、账号、Cookie version、egress address 和异常原文成为 metrics label。
- 凭据创建、激活、验证、撤销和租约只记录 actor、Provider、非 Secret 资源 ID、时间与结果。
- Cookie、Authorization、visitor data、PO Token 和临时文件路径进入日志过滤器和敏感字段测试。
- POT 上游子进程可能输出 token 和绑定标识，因此 PID1 supervisor 必须以 `stdio: "ignore"` 同时隔离 stdout/stderr；容器持久日志只允许 supervisor 的固定、无密故障事件。
- 单 Provider blocked 不影响 API readiness；kill switch 只阻止对应 capability/access mode 的新高成本任务。

## 15. 许可证与供应链

| 组件 | 许可证 | 约束 |
| --- | --- | --- |
| yt-dlp | Unlicense；发行物含其他依赖许可证 | 固定 commit、更新 canary、镜像 SBOM |
| bgutil POT Provider | GPL-3.0 | 当前插件/sidecar 固定 `1.3.2` 和 OCI digest，单独记录 SBOM/许可证并保持语义健康检查 |
| MeTube / cobalt | AGPL-3.0 | 只借鉴设计，不复制或内嵌源码 |
| gallery-dl | GPL-2.0 | 独立 Runner 候选，分发与源码义务单独评估 |

CI 应拒绝未登记许可证、未固定版本或可从用户目录动态加载的 Provider 插件。

## 16. 决策门与迁移

1. `AGENTS.md`、`SECURITY.md`、根/后端 README 必须持续保持本文的受控会话边界；普通 JSON 与 Generic 仍禁止 Cookie。
2. Phase 1 只允许 YouTube 运维会话；其他 Provider 要有真实 canary 和域名 allowlist 后才能启用。
3. 用户 Credential 在 Vault/Broker、跨 owner 隔离、删除和审计通过前不得上线。
4. 已进入默认拓扑的 POT sidecar 必须持续固定版本/digest、同步 SBOM 和许可证；版本库托管的 PID1 supervisor 必须保持 `/ping` 版本/连续失败恢复、子进程输出隔离和 internal-network 门禁。gallery-dl 仍需通过许可证、网络及故障隔离门禁后才能进入生产镜像。
5. Cookie 功能不扩大到私有、会员、购买或 DRM；若产品边界变化必须另立 Design/PRD 和法律评审。

实现顺序和验收见同编号 Plan 与 Acceptance。
