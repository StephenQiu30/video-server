# 红果短剧 Provider 接入调研

- 日期：2026-08-12
- 调研范围：GitHub 仓库检索、源码链路核验、许可证/来源审查、离线自测与构建可复现性
- 当前结论（2026-08-27）：**需要区分官方网页分享单集、用户已合法取得的 clear 文件和红果 App 受保护媒体**。窄范围 `hongguo_web` Provider 只处理官方分享页当前指向的一集，暂保持 `unknown`；用户 clear 文件可走 019/023 导入。下文对 App 签名/CENC 的源码核验只保留为历史风险证据，不再是产品实现候选；Android/模拟器 Edge Agent 不得读取 App 会话、取得密钥或转换受保护媒体。App/受保护内容只有在正式合同/API 按资产明确授予下载/导出权且输出未加密时，才可另立 Official Connector 评审。

## 0.1 官方分享单集路径（2026-08-17 新增）

用户提供的官方分享页会将当前集信息写入 H5 的 SSR `window._ROUTER_DATA`，其中包含剧集 ID、当前 `vid` 和章节顺序。分享页自身的 `series_data.play_url` 是带 `start=0&end=30` 的预览地址，不能作为完整单集来源。

`hongguo_web` 的处理边界如下：

1. 只接受 `novelquickapp.com` 官方分享短链/H5 路由和 `hongguoduanju.com` 官方播放器 URL。
2. 校验分享页的 `series_id`、当前 `vid` 与 `chapter_ids[chapter_order - 1]` 一致。
3. 使用同一组 ID 打开官方播放器页面，校验播放器返回的 `series_id` 与 `vid`。
4. 只接受第一方播放器状态里的 `v3-*.qznovelvod.com` HTTPS MP4 地址，并保留官方播放器 Referer；短时签名 URL 不持久化。
5. 输出单个 `source-mp4` format，后续继续经过现有 Runner 的 ffprobe、下载、Hash、Artifact 和分析链。
6. 不返回 `chapter_ids` 作为 playlist，不遍历其他集，不把分享页的预览地址升级为完整视频。

对用户提供的《佳偶错成》分享页，实际验证到第 1 集：197.6 秒、1280×720、MP4；远程 ffprobe 返回相同的 197.6 秒。该证据只证明“官方分享当前集”路径，不证明红果 App 全集或任意红果链接可用。

## 0. 可实现性判定

| 目标形态 | 可行性 | 信心 | 判定 |
| --- | --- | --- | --- |
| 用户上传已获取的红果/推广中心 MP4 后分析 | 高 | 高 | 现有 Artifact 与分析链可直接复用，只缺上传入口和来源标识 |
| Android/模拟器处理官方 App 受保护剧集 | 技术证据存在，产品不可采用 | 高 | 依赖 App 会话、私有签名、设备注册、内容密钥和 CENC 转换，违反当前 Edge clear-file 边界 |
| 服务端对分享链接直接下载 | 低 | 中 | 未找到无设备签名、无第三方解析服务且可复验的官方 App 实现 |
| 直接复制某个开源项目进入商业产品 | 低 | 高 | 最完整仓库无 LICENSE；另一仓库虽带嵌套 MIT，但源码来源、历史和打包二进制不足以证明可直接复用 |

因此，下文“技术链可复现”只说明社区方案的风险和媒体形态，不构成独立实现、产品接入或绕过保护的批准；候选源码、算法、二进制和协议不得进入产品。

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

仓库区分三类来源，但只有前两类能由平台直接取得字节：

- 匿名 Provider：只处理可正向证明公开、免费、非 DRM 且用户有权下载的 HTTP(S) 内容。
- 官方授权 Provider/Connector：必须获得正式 API/SDK、合作合同、资产级下载/导出权益和可审计样本；输出必须未加密，DRM/加密输出仍拒绝。
- 用户设备 Edge Agent：只传输用户已经合法取得并通过文件选择器显式选择的 clear 文件；不访问红果 App 会话、网络、缓存、签名或保护材料。

会员/播放权益、技术可播放或用户权利声明都不能解除保护。不得把设备登录态、签名、内容密钥或媒体转换放入 Edge；不得修改平台权益、将用户 URL 发给公共解析 API，或把影视聚合镜像冒充成红果官方来源。

## 5. 推荐接入顺序

### 5.1 用户原始媒体导入

首期允许用户上传其拥有下载和分析权利的红果原始视频文件。服务端对完整文件执行大小、时长、容器、音视频轨、SHA-256 和恶意输入边界校验，生成与下载任务相同可信度的媒体 Artifact，再复用现有 RabbitMQ、完整视频 Agent、报告与 MinIO 链路。

上传来源应显示为“红果原始媒体导入”，不能宣称系统从红果分享链接完成下载。批量整剧首期按单集产生独立 Artifact 和分析任务，跨集汇总另立需求。

### 5.2 用户设备 Edge Agent

Edge 只复用 019 的签名设备文件传输：用户通过系统文件选择器提交已经合法取得的 clear MP4，本地做大小、SHA-256、容器/轨道和保护标记预检，服务端在 quarantine 中独立复验。`declared_origin=hongguo` 只是审计标签，不写 Provider canary，不证明平台链接下载。`ProviderAccessMode` 不新增设备值；Edge 使用独立 `verified_import` execution mode。

### 5.3 官方授权 Provider

取得官方合作资料后新增独立 `hongguo-authorized-v1` Adapter：

1. 只接受官方声明的入口和媒体域名，重定向后重新执行 URL admission。
2. 通过版本化、只读 Secret 调用官方 API/SDK，不接收普通 API 请求中的 Cookie、Token 或设备参数。
3. inspect 必须返回作品、剧集、授权主体、资产级可下载/导出权益、保护方式和短时 clear 格式；权益或保护未知时 fail closed。
4. 下载前按原作品与剧集重新解析，不持久化短时 CDN URL；不请求许可证或内容密钥，不处理加密输出。
5. 官方接口只有播放权而没有下载/分析权时返回 `provider_content_restricted`，不能因为技术上可播放就生成 Artifact。
6. Provider Runner 与数据库、RabbitMQ、MinIO 和 AI 凭据隔离；下载结果继续经过 FFmpeg/ffprobe、大小、时长和 SHA-256 校验。

官方授权 Adapter 不应伪装成 yt-dlp Cookie extractor。当前 `ProviderSessionStore` 只处理 Netscape Cookie 文件，需要先扩展为带 `credential_kind` 的 Provider Secret 抽象，并为官方权益证明建立独立、可测试的校验端口。

## 6. 发布门禁

红果从 `unsupported` 提升前必须同时具备：

1. 对应接入路径的权益证明：官方 Provider 需要 API/SDK、合作合同、资产级下载/导出授权和 clear 输出；Edge clear-file import 只验证导入能力，不能提升红果 Provider。
2. 至少一个项目自有或明确授权剧集的 metadata、完整媒体和 analysis 三阶段证据。
3. DRM、无下载权、会员权益、过期授权、错误剧集、短链跳转和 schema 变化负例。
4. 下载前 re-inspect、完整文件 ffprobe/SHA-256、MinIO Artifact、RabbitMQ、Agent、报告与 WebSocket E2E。
5. 许可证、代码来源证明、SBOM、Secret scan、日志脱敏和单 Provider/Connector 隔离。
6. 若包含 Edge clear-file import，其安装包签名、每安装独立密钥、一次性上传 URL、本地工作区清理，以及“不访问平台域名/会话/缓存/密钥”的流量验收只批准 Import Profile。

在这些条件完成前，API 和前端不得将红果标记为 `verified`，也不得以第三方解析站或 Edge 文件导入的成功结果替代官方 Provider/Connector 端到端证据。

## 7. 实施前置输入

代码实施需要至少一种输入：

- 红果官方创作者/合作 API 或 SDK 文档，以及明确包含下载和自动化分析权利的授权；或
- 用户已经合法取得且拥有处理权利的 clear 原始视频样本，用于实现媒体上传与分析入口。

没有正式接口/合同/clear 输出时只能保留 `hongguo_web` 的窄范围候选和 clear 文件导入；不能形成红果 App 下载能力。
