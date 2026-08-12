# 红果短剧 Provider 接入调研

- 日期：2026-08-12
- 调研范围：GitHub 仓库检索、源码链路核验、许可证/来源审查、离线自测与构建可复现性
- 总结论：**技术上可实现，产品化为有条件可行**。不适合实现为纯服务端、无状态、匿名公网 extractor；推荐 Android/模拟器 Edge Agent 在本地完成签名、取链与媒体转换，只向服务端交付标准 MP4 制品。当前代码尚未实现，Provider 保持 `unsupported`

## 0. 可实现性判定

| 目标形态 | 可行性 | 信心 | 判定 |
| --- | --- | --- | --- |
| 用户上传已获取的红果/推广中心 MP4 后分析 | 高 | 高 | 现有 Artifact 与分析链可直接复用，只缺上传入口和来源标识 |
| Android/模拟器 Edge Agent 下载官方 App 剧集 | 中 | 中 | 完整技术链已有两份源码佐证，但签名、设备注册和风控对 App 版本/设备敏感 |
| 服务端对分享链接直接下载 | 低 | 中 | 未找到无设备签名、无第三方解析服务且可复验的官方 App 实现 |
| 直接复制某个开源项目进入商业产品 | 低 | 高 | 最完整仓库无 LICENSE；另一仓库虽带嵌套 MIT，但源码来源、历史和打包二进制不足以证明可直接复用 |

因此，这里的“可实现”是指可以按已验证的协议和算法独立实现，不是指可以无审计地将候选仓库整库搬入。

## 1. 调研方法

调研同时使用仓库名、中英文关键词与关键协议字段检索，包括 `红果短剧`、`hongguo downloader`、`com.phoenix.read`、`spade_a`、`multi_video_model`、`CENC` 和 `X-Argus`。候选项目按以下门槛逐层筛选：

1. 目标必须是红果官方 App/官方创作者工具，不是影视聚合站换皮。
2. 必须追踪到真实的 catalog、media model、短时 CDN URL 与最终可播制品，不只看 README 或 UI。
3. 必须分开“有代码”、“可构建”、“有离线真值自测”和“需真机/账号才能验收”。
4. 许可证、第三方代码来源、硬编码凭据/设备信息、二进制交付和单点第三方 API 依赖均是独立否决项。

## 2. GitHub 候选核验

以下为 2026-08-12 的快照。Star 和 Fork 只表示社区覆盖面，不代表产品可用性。

| 项目 | 快照 | 源码实际覆盖 | 复现结果 | 许可/来源 | 决策 |
| --- | --- | --- | --- | --- | --- |
| [`zhangbaio/hongguo`](https://github.com/zhangbaio/hongguo) | 37 Star / 22 Fork，2026-07-14 仍更新 | 官方 `com.phoenix.read`；搜索/剧集→`multi_video_model`→`spade_a`→CENC AES-CTR→MP4；Frida 签名预言机 | 关键 Python 文件编译通过；`unwrap_spade.py` 5/5 真值向量通过；无设备时无法复验在线签名 | 顶层无 LICENSE | **最强技术证据，禁止复制源码**；仅用于协议分层和验收向量参考 |
| [`lingbol088-spec/short-drama-downloader`](https://github.com/lingbol088-spec/short-drama-downloader) | 42 Star / 35 Fork，2026-07-24 仍更新 | 包含离线签名模块、`multi_video_model`、`spade_a` 密钥派生、CENC 转换与 Windows UI | Python 全量编译通过；无离线真值测试和可自动的端到端验收 | 嵌套源码目录有 MIT，但仓库主体以 ZIP/EXE/单次快照交付，含硬编码设备样例，原始代码来源未建立可追溯记录 | **第二份技术佐证**；在来源审计前不复制代码、不分发内置二进制 |
| [`Erlmo/shortplay`](https://github.com/Erlmo/shortplay) | 27 Star / 3 Fork，2026-07-02 仍更新 | Flutter 播放器和 CENC 流式播放框架 | README 明确说明 `spade_a` 等核心算法不开源 | 无 LICENSE，关键实现缺失 | 只证明媒体形态，不是下载 Provider 基线 |
| [`HanFeng151519/hongguo`](https://github.com/HanFeng151519/hongguo) | 1 Star，2026-06-12 仍更新 | 红果检索，以番茄达人中心 `batch_download` 获取明文素材 | Python 编译通过；需用户 Cookie、`msToken` 和 `a_bogus` | 无 LICENSE | 可作为**已有创作者/推广中心权限**的另一接入路径，不代表普通红果 App 下载 |
| [`KeepThinking007/HongGuoData`](https://github.com/KeepThinking007/HongGuoData) | 22 Star / 2 Fork，2026-04-12 仍更新 | Phone Agent 采集榜单、介绍和互动数据 | 不交付视频媒体 | Apache-2.0 文件存在 | 仅作元数据研究参考 |
| [`acaiblog/CastTV-DLNA`](https://github.com/acaiblog/CastTV-DLNA) | 5 Star / 4 Fork，2026-05-11 仍更新 | 无障碍遍历 + DLNA，尝试用正则提取 M3U8/MP4 | 源码中关键 API 标注为占位实现，包名也是猜测集合，无 CENC 处理 | README 称 MIT，顶层无 LICENSE | 不能证明下载链路，排除 |

[`zhangbaio/hongguo-downloader`](https://github.com/zhangbaio/hongguo-downloader) 依赖第三方付费解析 API 和机器码，[`wangduoyu001/hongguo-drama-downloader`](https://github.com/wangduoyu001/hongguo-drama-downloader) 实际抓取 `hongguoapp.cn` 苹果 CMS 聚合站；两者都不能证明官方红果 App 的可控产品链。[`yt-dlp/yt-dlp`](https://github.com/yt-dlp/yt-dlp) 当前没有红果或 `com.phoenix.read` extractor。

## 3. 技术链与实测证据

两个分别发布的候选仓库可相互佐证如下链路；但它们之间是否存在未声明的代码继承关系仍需来源审计：

1. 通过剧集 ID/分集 VID 调用 `multi_video_model`，获得短时 `main_url`、画质和 `encrypt_info.spade_a`。
2. API 请求需要客户端签名；完整仓库使用已运行的红果 App + Frida 签名预言机，另一仓库带离线签名实现，但缺少可追溯性和真值测试。
3. `spade_a` 可本地派生 16 字节内容密钥；MP4 的 `senc` 提供 base IV，然后按 CENC AES-128-CTR 逐 sample 转换。
4. 本次在全新浅克隆上执行 `python3 frida/unwrap_spade.py`，5 组内置真值向量全部通过；`offline_dl.py`、`hongguo.py`、`offline_decrypt.py`、`server.py` 编译检查通过。
5. 尚未完成真实端到端下载，因为当前环境没有已配对的 Android/模拟器、指定红果 App 版本和可用于验收的单集样本。

最大的产品化风险不是 AES 算法，而是取得 `main_url + spade_a` 前的客户端签名和设备生命周期。候选仓库已记录 App 大版更新会使 hook 入口失效，且批量新 device ID 会遇到风控。所以不能把它伪装成可水平扩展的无状态 Runner。

## 4. 产品决策

仓库不再把所有 DRM 内容永久排除，而是区分三类访问模式：

- 匿名 Provider：继续只处理公开、非 DRM、用户有权下载的 HTTP(S) 内容。
- 官方授权 Provider：可以处理平台保护内容，但必须获得官方 API/SDK、合作授权、明确的下载/分析权益和可审计的授权样本，并通过独立安全设计、Provider canary 与验收。
- 用户设备 Edge Agent：在用户控制的 Android 设备/模拟器和已授权红果会话中处理设备协议与受保护媒体，只向服务端上传标准媒体制品与脱敏元数据。

删除“非 DRM”这一全局硬边界，不等于把设备登录态和密钥带入中心服务。设备协议、签名和媒体转换都必须留在 Edge Agent 的单任务工作区中，任务完成后销毁临时参数。不得修改平台权益、将用户 URL 发给公共解析 API，或把影视聚合镜像冒充成红果官方来源。

## 5. 推荐接入顺序

### 5.1 用户原始媒体导入

首期允许用户上传其拥有下载和分析权利的红果原始视频文件。服务端对完整文件执行大小、时长、容器、音视频轨、SHA-256 和恶意输入边界校验，生成与下载任务相同可信度的媒体 Artifact，再复用现有 RabbitMQ、完整视频 Agent、报告与 MinIO 链路。

上传来源应显示为“红果原始媒体导入”，不能宣称系统从红果分享链接完成下载。批量整剧首期按单集产生独立 Artifact 和分析任务，跨集汇总另立需求。

### 5.2 用户设备 Edge Agent

开源项目证明红果的关键不是 yt-dlp extractor，而是一个与官方 App 共置的设备端采集器。首期按以下边界独立实现，不拷贝无许可证仓库的源码：

1. `Session Adapter` 只在本地调用已登录 App 会话，服务端看不到 Cookie、Token、设备参数和签名中间值。
2. `Catalog Adapter` 将剧集、分集、标题、封面、时长和质量规格映射为稳定 manifest；每集一个独立任务。
3. `Media Adapter` 在设备本地完成短时媒体获取和受保护媒体转换，不上传密文链接、许可响应、签名材料或内容密钥。
4. `Artifact Packager` 执行 ffprobe、容器/音视频轨、时长、大小和 SHA-256 校验，再通过一次性上传会话提交 MP4 与脱敏 manifest。
5. 服务端重新计算 SHA-256 并执行 ffprobe，通过后生成 MinIO Artifact，后续复用 RabbitMQ、完整视频 Agent、报告和 WebSocket 链路。

当前 `ProviderAccessMode` 只有 `anonymous/operator_managed`；实施时应新增 `user_device`，并将它路由到设备任务协议，不得降级到普通 Media Runner。

### 5.3 官方授权 Provider

取得官方合作资料后新增独立 `hongguo-authorized-v1` Adapter：

1. 只接受官方声明的入口和媒体域名，重定向后重新执行 URL admission。
2. 通过版本化、只读 Secret 调用官方 API/SDK，不接收普通 API 请求中的 Cookie、Token 或设备参数。
3. inspect 必须返回作品、剧集、授权主体、可下载权益、DRM/保护方式和短时格式；权益未知时 fail closed。
4. 下载前按原作品与剧集重新解析，不持久化短时 CDN URL、许可证响应或内容密钥。
5. 官方接口只有播放权而没有下载/分析权时返回 `provider_content_restricted`，不能因为技术上可播放就生成 Artifact。
6. Provider Runner 与数据库、RabbitMQ、MinIO 和 AI 凭据隔离；下载结果继续经过 FFmpeg/ffprobe、大小、时长和 SHA-256 校验。

官方授权 Adapter 不应伪装成 yt-dlp Cookie extractor。当前 `ProviderSessionStore` 只处理 Netscape Cookie 文件，需要先扩展为带 `credential_kind` 的 Provider Secret 抽象，并为官方权益证明建立独立、可测试的校验端口。

## 6. 发布门禁

红果从 `unsupported` 提升前必须同时具备：

1. 对应接入路径的权益证明：官方 Provider 需要 API/SDK 与合作授权；Edge Agent 需要用户内容权利声明、自有设备绑定与明确授权样本。
2. 至少一个项目自有或明确授权剧集的 metadata、完整媒体和 analysis 三阶段证据。
3. DRM、无下载权、会员权益、过期授权、错误剧集、短链跳转和 schema 变化负例。
4. 下载前 re-inspect、完整文件 ffprobe/SHA-256、MinIO Artifact、RabbitMQ、Agent、报告与 WebSocket E2E。
5. 许可证、代码来源证明、SBOM、Secret scan、日志脱敏、单 Provider 隔离和设备撤销/轮换演练。
6. Edge Agent 安装包签名、每安装独立密钥、一次性上传 URL、本地工作区清理，以及“不上传平台会话/密钥”的流量验收。

在这些条件完成前，API 和前端不得将红果标记为 `verified`，也不得以第三方解析站的成功结果替代官方 Provider 或 Edge Agent 端到端证据。

## 7. 实施前置输入

代码实施需要至少一种输入：

- 红果官方创作者/合作 API 或 SDK 文档，以及明确包含下载和自动化分析权利的授权；或
- 用户拥有权利的原始视频样本，用于先实现媒体上传与分析入口；或
- 一台用户控制的 Android 设备/模拟器、已登录红果 App 和明确授权的单集测试样本，用于实现并验收 Edge Agent。

没有上述输入时只能完成控制面和 fail-closed 骨架，无法形成真实可用的红果下载能力。
