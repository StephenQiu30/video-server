# 031 可移植个人部署与平台访问设计

- 状态：无会话隔离启动、访问状态投影、macOS 本机专用浏览器 Agent 与产品内授权引导已实现；loopback/Unix Socket 的产品内一次性授权事务和跨平台 clean-room 真实验收仍待实现。
- 用户范围：个人使用；全部服务和验收均运行在当前宿主，不要求任何额外设备或常驻 Provider Node。任意全新隔离部署不以 Cookie 文件作为核心服务启动前置条件。Linux 仍是可用目标，不要求企业授权平台。
- 关联：运维手册见 [008 个人部署重启与换机手册](../operations/008-个人部署重启与换机手册.md)。历史过程通过 Git 追溯。

## 设计结论

项目必须区分“软件可移植”与“第三方平台授权可移植”：

- 软件、匿名解析器、JS Runtime、PO Token Provider 和能力探测必须随 Compose 自包含，在新宿主无会话文件时也能启动。
- 登录态、验证码通过状态、Visitor ID、出口信誉和账号权益由第三方平台控制，不能从 Git 仓库、镜像或算法中凭空恢复，也不能承诺任意新出口始终通过风控。
- 产品目标是消除手工导出、复制和挂载 Cookie 的日常流程，而不是绕过平台验证。需要验证时，由本机受控浏览器完成一次交互授权并持续复用；平台未要求验证时始终使用匿名路线。
- 不建设常驻 Provider Node，不把用户会话上传到 FrameFetch 服务，也不依赖公共 Cookie、公共代理或第三方下载站。

因此，“全新部署开箱即用”的可判定含义是：核心服务正常启动、所有平台完成当前宿主能力探测、公开路线可用的平台立即可用；被平台要求验证的平台显示明确的本机授权动作，完成一次后由本机自动维护，不要求用户准备 Netscape 文件。当前 v1 通过 macOS 本机 Agent 命令完成这次授权；产品内直接启动 Agent 的 loopback/Unix Socket 事务仍是后续交付项。

## 便携访问阶梯

每个平台使用同一个有限状态机，不在前端或业务 Worker 中写平台特例：

1. `public_probe`：先使用匿名 Runner；YouTube 同时使用本地 PO Token Provider。新部署不得因为缺少 operator profile 或 Cookie 目录而启动失败。
2. `public_ready`：metadata 与有界 media 探针均成功后开放公开下载；结果绑定当前 engine、出口与上下文 generation。
3. `authorization_required`：只有稳定错误明确指向登录、验证码或出口挑战时进入，不把链接失效、地区限制、DRM、解析器 bug 或超时伪装成授权问题。
4. `local_authorization`：API 创建一次性授权事务，本机 Access Agent 打开 Provider 专用持久浏览器目录；用户只在平台页面完成其要求的登录或验证。应用不得要求复制 Cookie 文本。
5. `operator_ready`：Agent 仅发布该 Provider allowlist 内的会话快照，Runner 每次操作读取；后台按 revision 更新并由 Canary 验证。
6. `degraded`：匿名和本机授权路线均不可用时，平台保持降级并返回稳定原因与下一步，不循环登录、不切换未知代理、不把失败链接计为平台整体失效。

路由只允许从匿名路线显式升级到同机、同 Provider 的 operator 路线。一次 inspection 冻结访问上下文；下载阶段不能静默换账号、出口或策略。

## 本机 Access Agent

Access Agent 是部署在同一宿主上的可选组件，不是常驻远端服务：

- 使用 FrameFetch 专用浏览器数据目录，不读取、复制或上传用户的完整 Chrome Profile。
- 授权事务由短时 nonce、Provider、过期时间和本机 HMAC 绑定；仅接受 loopback/Unix Socket 请求。
- 每个平台独立目录、进程、Cookie allowlist 和并发租约；一个平台的授权不能被另一个 Runner 读取。
- 首次挑战允许在当前宿主打开可见浏览器；成功后普通 Compose/容器重启自动复用。只有平台撤销授权或当前部署再次被挑战时才重新交互。
- 无桌面 Linux 仍可运行匿名路线；如果平台明确要求交互验证，该平台应显示 `authorization_required`，不能伪装成无人值守可用。
- 文件会话和 `.ffsession` 继续作为高级导入/灾备能力，但不再是默认安装步骤，也不是 clean-room 启动条件。

Access Agent 不能自动点击验证码、规避风控或保证会话永久有效。它解决的是产品内授权和自动维护，而不是突破第三方平台安全边界。

## 启动与能力发现

API readiness 只反映 FrameFetch 核心依赖，不因可选 Provider 授权缺失返回失败。启动后 Canary 异步执行：

- 静态检查：Runner、解析器、JS Runtime、FFmpeg、PO Token Provider 与配置版本。
- metadata 探针：区分解析器失败、链接失效、平台验证、出口挑战和地区/权益限制。
- media 探针：下载小型固定公开样本并验证容器、时长、音视频流和哈希预算。
- 状态投影：`public_probe`、`public_ready`、`authorization_required`、`operator_probe`、`operator_ready`、`degraded`、`blocked`、`disabled`、`unsupported`；不得仅凭容器健康或 Cookie 文件存在显示“可用”。

全新隔离部署第一次启动不阻塞等待 24 个真实媒体下载。核心页面可立即使用，平台状态逐项更新；用户提交链接时，如果该 Provider 探针尚未完成，允许执行一次有界按需探针，不能无限等待或排队假任务。

项目没有额外验收机器。无状态启动通过当前宿主上的 clean-room 环境验证：使用独立 Compose project、独立临时卷和独立浏览器目录，不挂载现有 `.provider-sessions` 或用户数据。该验收能够证明代码和启动流程不依赖旧私有状态；由于仍共享当前宿主的公网出口，它不能证明另一公网 IP 一定不触发平台验证，后者也不作为本项目交付前置条件。

## 不可承诺的边界

以下目标在没有常驻可信节点、官方下载 API 或第三方平台配合时不可实现，不能写入验收标准：

- 任意公网 IP、任意时间、所有 24 个平台都无需验证即可下载。
- 将 Cookie、Visitor ID 或 PO Token 固化进仓库后永久跨机器有效。
- 使用公共代理、轮换住宅代理、验证码绕过或共享账号来保证成功率。
- 对 DRM、会员权益、地区限制或平台明确禁止下载的内容自动降级绕过。

“根本解决”以产品行为衡量：新部署不因私有状态缺失而损坏；可匿名的平台自动可用；必须验证的平台在 UI 内完成一次授权并自动复用；无法合法获取的内容给出准确状态，不再要求操作者反复执行 Cookie 导出命令。

## 问题与最小方案

原生产 Compose 默认启动九个受控 Runner，却全部依赖容器外的 macOS 会话代理和 Chrome 状态。代码和镜像存在并不能恢复这些宿主条件。当前工作机已安装代理且容器显示健康，尚未取得重启前后同一平台的真实失败样本，因此不能把全部故障都归因于会话丢失。

个人使用不新增远端凭据数据库、独立授权服务或工作流引擎。沿用现有任务数据库、Outbox、队列和制品存储。当前部署方维护的只读 Netscape Cookie 文件来源保留为过渡及灾备通道；目标默认路径由本机 Access Agent 管理 Provider 专用持久目录和受限会话发布。配置和会话放在本机持久目录，操作临时文件仍只存在于 tmpfs。重建容器不删除本机来源，clean-room 部署在无来源时仍以匿名能力启动。

## 当前实现

- `ProviderAccessState` 已将当前宿主/出口的探针证据投影为公开线路待验证、公开可用、需要授权、受控线路待验证、受控线路可用、降级、受限、停用和不支持；`egress_challenged`、`pot_required`、`pot_rejected` 等稳定错误不会再被误报为普通解析器故障。
- macOS 已提供按 Provider 隔离的本机授权 Agent v1：`authorize --provider <key>` 打开第一方页面并轮询专用 Chrome 数据目录，`install --browser-root ...` 安装按需 LaunchAgent。授权数据只留在当前宿主，子进程只产生内存中的受限租约，不落项目 Cookie 文件。当前 Agent 支持 Chrome-backed Provider；视频号仍走独立元宝来源，腾讯视频/优酷仍走受控文件来源。
- 平台状态页已展示上述访问状态，并在 `authorization_required` 且存在受控线路时给出本机授权步骤。由于浏览器不能安全地从容器内直接启动宿主命令，当前引导仍是显式本机命令；它不是目标中的公共代理或远端常驻节点。
- `RunnerSettings.runner_provider_cookie_file` 与 macOS 的 `runner_provider_cookie_sync_root` 二选一；匿名 Runner 禁止配置任一来源。
- [文件读取器](../../backend/app/workers/runner/provider_cookie_file.py)每次操作重新打开文件，限制 1 MiB、普通文件、无最终符号链接、无硬链接、无其他用户权限，并校验平台域、格式、到期时间和必需 Cookie 名。普通用户 API 不接受 Cookie。
- [会话装配](../../backend/app/workers/runner/provider_sessions.py)继续生成唯一的 `0600` 操作 jar。文件来源的访问上下文使用带密钥摘要形成不透明版本；文件替换后旧任务不能静默使用新会话。只要有效负载与部署 HMAC 密钥不变，路径和机器变化不会改变版本。
- 操作期间 Cookie 更新只写临时副本，不覆盖只读来源；此模式不会自动延长会话寿命，也不证明平台端未撤销授权。换机后平台要求重新验证与程序重启丢配置是不同事件。
- 两套 Compose 对 YouTube、抖音、Reddit 使用按平台隔离的本机 Agent 队列挂载；视频号继续使用元宝动态来源，优酷/腾讯视频保留按平台只读文件来源。队列只传递一次性加密租约，不把浏览器目录或 Cookie 文件挂进容器，也不把全部平台会话挂到同一 Runner。
- 两套业务 Compose 的受控 Runner 均按 profile 启用。生产示例默认不配置受控路由，个人只保存已配置的平台组合，避免未安装的会话来源阻止启动。
- 视频号仍依赖元宝动态浏览器状态，按 035 批准改用本机专用持久登录目录；文件模式明确拒绝。用户首次登录与来源恢复独立验收，不能以目录存在宣称纯 Linux 或新机已可下载。

## 启动、更新与迁移

启动继续使用固定镜像和 lockfile，不在每次启动时修改解析器参数或升级依赖。平台变化通过现有构建与测试工作流发布更新。任务恢复复用 030 和既有 lease/Outbox，不在本次改变重试预算或跨主机执行机制。

匿名能力不需要首次配置。平台要求验证时，当前 v1 由宿主上的本机 Agent 建立一次 Provider 专用来源，后续普通 `restart`、`up --force-recreate` 自动复用；产品内 loopback/Unix Socket 授权事务尚未交付。更换手机、平板或前端浏览器时仍由同一后端持有平台会话，客户端不搬运 Cookie；更换运行后端的宿主时，平台通常仍要求在新宿主第一方页面完成一次登录，这是第三方平台的设备/出口边界，不能由应用凭空迁移。`.ffsession` 只保留为可选灾备能力，不得成为安装前置条件。HMAC 密钥、出口身份等上下文变化时旧任务应重新解析，不能取消既有身份隔离规则。详细操作见[个人部署与迁移](../operations/008-个人部署重启与换机手册.md)。

## 验收标准

1. 在当前宿主创建不挂载 `.provider-sessions`、operator profile 和既有浏览器状态的 clean-room Compose project，核心 readiness 成功，首页与平台状态可访问。
2. 对固定公开样本分别记录 metadata 与 media 结果；匿名成功的平台无需任何授权文件。
3. 构造 `egress_challenged` 或 `credential_required`，UI 只展示一次“完成平台验证”动作；完成后无需 CLI、Cookie 粘贴或容器重建即可重试原链接。
4. 重启 Docker 与整机后，本机已授权 Provider 自动恢复；撤销授权后准确回到 `authorization_required`，不循环重试。
5. 删除 clean-room 临时卷后重新创建同一隔离项目并重复第 1 项；不得读取当前业务部署的浏览器 Profile。恢复灾备包属于可选验证，与开箱启动分开记录。
6. 平台可用声明必须来自当前宿主、当前出口的真实 metadata/media 证据；静态测试、健康检查和旧机器截图不能替代。

## ToC 工具依据

2026-09-07 通过 GitHub 插件读取官方仓库：

- [MeTube README](https://github.com/alexta69/metube/blob/master/README.md)：持久 STATE_DIR 保存队列与历史，提供 Cookie 导入和单独的 yt-dlp 更新途径。这支持把个人状态与软件更新分开管理，不需要每次启动重新适配。
- [YTDLnis README](https://github.com/deniscerri/ytdlnis/blob/main/README.md)：提供 Cookie 支持和应用内更新入口。它不是无需维护的平台协议实现；这里只借鉴个人产品的配置与更新体验。
- [yt-dlp FAQ](https://github.com/yt-dlp/yt-dlp/wiki/FAQ)：媒体请求可能绑定 Cookie、IP 和请求头。相同文件换机器不构成所有平台必然可用的证明，仍需实际验证。

031 当前已交付无会话启动、访问状态机、macOS 本机专用浏览器 Agent v1 和平台状态页授权引导；产品内 loopback/Unix Socket 一次性事务、完整自动恢复和 clean-room 真实平台矩阵仍按 BACKLOG P6 实施。新增平台接入见 [032](032-腾讯视频与优酷个人下载设计.md)。本轮没有宣称所有平台真实下载或跨宿主授权迁移已完成。
