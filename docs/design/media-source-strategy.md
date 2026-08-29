# 媒体解析策略责任链与 Provider Session 生命周期

- 状态：当前设计事实；外部 Provider 真实可用性由 canary 持续判定
- 关联设计：`005-多平台Provider策略设计.md`

## 1. 问题与目标

解析入口原先在 `MediaRunnerRouter.inspect` 中直接嵌套匿名与 Operator
异常处理。它能够工作，但路由顺序、允许降级的错误和最终错误优先级耦合在
同一个方法中；YouTube 登录 Cookie 被浏览器轮换后，Runner 又会把带 Cookie
的 bot challenge 误报为出口验证失败，导致用户只能看到“稍后重试”。

本设计完成六个目标：

1. 用可测试的策略责任链统一匿名与 Provider Operator 解析路径。
2. 以错误策略对象约束降级范围，并优先暴露已配置会话过期。
3. Operator 会话只来自部署环境提供的版本化只读 Secret；运行时不读取个人浏览器，
   不依赖开发者电脑或 AI Worker，也不提供普通用户 Cookie 上传入口。
4. 私有封面通过认证 HTTP client 获取并在内存中显示，不让原生图片请求绕过
   Access/Refresh Cookie 恢复。
5. 下载任务由 Worker 在执行前重新解析并校验规格；终态重试只负责入队，避免
   Provider 的短时不稳定直接阻断 HTTP 操作。
6. 为 Registry 中每个平台维护固定 metadata/media 诊断样本，并把真实结果写入
   canary 表；没有当前证据时不再显示静态“已验证”日期。

## 2. 解析管线模式

```mermaid
flowchart LR
    API["MediaRunnerRouter facade"] --> P["MediaInspectionPipeline"]
    P --> A["Anonymous runner strategy"]
    A --> F{"Failure policy permits fallback?"}
    F -->|No| E["Stable public-path error"]
    F -->|Yes| O["Provider operator strategy"]
    O --> S{"Operator result"}
    S -->|Success| R["Frozen access context"]
    S -->|Session expired| X["Session-expired diagnosis"]
    S -->|Other failure| E
```

采用的模式和边界如下：

- **Strategy**：每个隔离 Runner client 是一个可替换的解析策略。
- **Chain of Responsibility**：`MediaInspectionPipeline` 根据 Provider 生成有界
  的 `anonymous → operator` 尝试链，不穷举账号、client 或代理。
- **Policy Object**：`InspectionFailurePolicy` 独立决定是否继续和选择哪个稳定
  错误；鉴权、链接临时不可用、临时故障和平台验证错误才允许进入 Operator。
- **Facade**：`MediaRunnerRouter` 只协调解析管线、下载上下文路由和活跃任务，
  不再内嵌 Provider 错误分支。

限流、地域、DRM、内容权益、格式不支持等错误不会消耗 Operator 会话。若
Operator Cookie 已过期，管线返回会话过期，而不是保留匿名 bot challenge；
Operator 已确认链接失效时也优先返回这个确定结论，避免匿名提取器回归把失效内容
误报成平台临时故障。其他 Operator 基础设施故障仍保留匿名路径的原始诊断。

## 3. Provider Session 生命周期

C 端服务不能把任何个人电脑上的 Chrome Profile、Keychain、Codex Worker 或登录窗口
作为可用性前提。Provider Operator 因此是部署方可选能力，并遵循同一生命周期：

1. 部署方在仓库外完成账号授权，把最小 Netscape Cookie 文件写入 Secret 管理系统；
   应用不包含浏览器读取、登录自动化或 Cookie 导出代码。
2. 每个 Secret 只允许一个 Provider 的批准域，使用不可变版本名并以只读方式挂载到
   对应的物理隔离 Runner。
3. Runner 在单次操作内创建 `0600` 临时副本；Cookie 原文不进入 API、数据库、
   RabbitMQ、日志、业务响应或 AI Worker。
4. 新版本必须通过自有或明确授权样本的 canary 后才能激活；撤销时从路由移除对应
   Provider，停止 Runner 并删除 active/retained 版本。

微信视频号是明确例外：当前没有采用可供本服务代表任意用户授权和下载分享作品的官方
接口，因此 Profile 只有匿名模式，不配置 Operator Secret。匿名第一方响应未直接公开
clear 媒体时立即失败，并引导用户上传自己拥有或已获授权的文件。

## 4. 环境策略

| 环境 | 会话来源 | 生命周期 | 用途 |
| --- | --- | --- | --- |
| 本地开发 | 无真实账号或测试专用 Secret | 测试期 | 单元测试和隔离 Runner 契约 |
| CI | 无真实账号或短期测试 Secret | 测试期 | 单元测试和授权 canary |
| 生产 | 受控 Secret 管理系统提供的专用账号版本 | 不可变、canary 后激活 | 可审计、可回滚的 Operator Runner |

若未来平台提供官方 OAuth 或资产导出 API，应新增官方 Connector，以用户授权范围和
资产级导出权替代 Cookie。不得把本地授权工具、消费端私有接口或浏览器自动化扩展为
服务器登录方案。

## 5. 验收条件

- 同一公开 YouTube 链接可由匿名失败后自动选择 YouTube Operator。
- 带 Cookie 的 bot challenge 分类为 `credential_expired`，页面给出可操作错误。
- 版本化最小 Secret 可由 Operator Runner 只读加载，仓库运行时没有浏览器获取代码。
- 视频号 Profile 只有匿名模式，匿名响应没有 clear 媒体时不进入任何会话回退。
- 解析成功后下载仍使用 inspection 冻结的 Operator access context。
- 限流等非白名单错误不触发 Operator，失败链保持有界。
- 目标链接完成解析、选格式、下载、制品校验和 AI 分析入口验证。

## 6. 私有封面交付

封面对象继续存储在私有 MinIO，并由受保护的 inspection 路由返回。前端不能把
受保护 API URL 直接交给图片标签，因为图片导航不会经过共享 HTTP client 的
401 刷新拦截器。`media-assets` 服务先用认证 client 读取 Blob，校验 MIME 与
非空内容，再创建短生命周 object URL；`MediaCover` 最终仍用官方 Next.js
`Image` 组件解码和渲染，并用 shadcn `AspectRatio` 维持布局。组件卸载或来源
改变时立即 revoke object URL。

站点 CSP 只为 `img-src` 增加 `blob:`，不扩大 script、connect 或 frame 来源。
加载中与真正失败是两个不同状态，只有认证读取或浏览器解码失败才显示“封面不可用”。

### 6.1 前端组件边界

- 业务组件只组合 `components/ui` 中的 shadcn/ui 组件；原生表单控件和
  Radix primitive 只能出现在该目录内。
- 图片使用官方 Next.js `Image`；受保护资源适配是数据层责任，不重新实现
  图片组件。
- Dialog、Sheet、Popover、Select、RadioGroup、Progress、Alert 与 Input
  优先使用已安装的 shadcn 实现，由 Radix 提供焦点、键盘和无障碍语义。
- `component-boundaries.test.ts` 扫描业务 TSX，阻止新增原生交互控件或越层
  导入 Radix。

## 7. 下载规格与重试边界

平台可能在两次请求间轮换 CDN rendition。创建任务时只校验用户刚刚选择的
inspection/format 仍属于当前账户；终态重试不会在 HTTP 请求中再次调用 Provider，
而是复用已保存的来源引用和语义计划创建新的持久化队列任务。解析记录过期不影响
这个入队动作。

Download Worker 在真正下载前必须使用原访问上下文重新 inspect，检查来源身份、权益
和当前可用流，再由 Runner 依据语义计划选择流。Provider format id 只是短期 hint，
不能作为恢复依据；若当前规格不可用，任务返回 `format_unavailable`，用户重新解析
链接后选择新的真实规格。重新 inspect 成功后，Runner 把本次解析结果以 `0600`
临时 JSON 保存在当前任务工作区，并用 `--load-info-json` 下载刚刚选中的流；任务结束
后随工作区清理。这样既不把会过期的 CDN URL 持久化到 PostgreSQL，也不会为了下载
再次触发平台网页挑战。媒体字节、封装和最终制品完整性校验仍不能绕过，也不改写
原任务历史。

## 8. 固定诊断矩阵与状态真实性

`fixed_public_cases.json` 为 22 个注册 Provider 各保存一条 versioned metadata 和
media 诊断样本；单元测试要求它和 Registry 精确双向覆盖。诊断命令只输出
Provider、Profile、阶段、结果、稳定错误码和耗时，不输出 URL 或 Cookie。

固定公开矩阵用于定位上游回归，不替代生产环境 Secret 配置的项目自有/授权
canary。Registry 的基线表示当前版本已经完成的发布验收，不会因为长期无人下载或
没有配置固定探针而退回 unknown；只有近期重复失败、平台限流、认证失败或出口受限
才临时覆盖该基线。尚未发布验收的 unknown Profile 仍必须同时具备 metadata、media、
完整视频 Analysis 证据和显式批准，才能提升为 verified。

所有成功并保留完整制品的真实远程下载都会自动投影为非敏感 media 运行证据；投影
只读取 Provider/Profile/访问模式和完成时间，不解密、不返回来源 URL，也不记录用户
身份。状态 API 因而能立即反映真实用户链路的最近下载时间，26 小时后仅把“当前可用”
标记转为历史时间，不撤销已经发布的支持能力。完整 Analysis 仍使用严格 attestation，
不能由普通下载推导。Compose readiness 只检查匿名 Media Runner 和业务核心依赖；
可选 Operator Runner 与平台 canary 的故障只降级对应平台，不让整个 API、上传、
匿名下载或 AI 配置不可用。

2026-08-29 的真实浏览器回归覆盖 22 个可启用 Provider：除小红书外均完成真实媒体
下载和制品校验；QQ 视频保持明确禁用。小红书当前公开入口由平台返回 `300012`
IP 风险限制，两个旧测试笔记由第一方页面返回 `300031` 已失效；系统分别保留平台
验证边界，并把确定失效的笔记归类为 `provider_link_unavailable`，不再伪报服务故障。
TikTok 解析使用其嵌入播放器实际调用的第一方 `player/api/v1/items`，网页挑战只作为
上游回退；真实任务以 H.264/AAC 在首次执行完成。Tumblr 公开页由项目插件直接读取
当前 `www` 页的 OG 视频与封面，避免上游旧 blog 子域改写触发 429。
