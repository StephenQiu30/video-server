# Provider 接入架构重构调研

- 日期：2026-08-26
- 范围：公开、非 DRM 单视频 Provider；不新增账号 Runner
- 结论：以 yt-dlp 官方 extractor/plugin 为解析扩展点，以项目内声明式 Profile 为安全与产品扩展点。

## 1. 上游事实

yt-dlp 官方支持两种与本项目直接相关的扩展方式：内建 extractor 可通过固定 `--extractor-args` 调整，可信的自定义 extractor 可放入 `yt_dlp_plugins.extractor` namespace 并按 URL 自动选择。官方同时提醒插件会被导入执行且不做代码安全检查，因此项目只能加载随镜像审计和测试的仓库插件，不能接受用户插件或目录参数。

- [yt-dlp README：Extractor Arguments、Plugins、Embedding](https://github.com/yt-dlp/yt-dlp/blob/master/README.md)
- [yt-dlp Plugin Development](https://github.com/yt-dlp/yt-dlp/wiki/Plugin-Development)
- [yt-dlp Extractors：YouTube 匿名、Cookie 与 PO Token 边界](https://github.com/yt-dlp/yt-dlp/wiki/Extractors)

Python `Protocol` 提供结构化端口而不要求继承共同基类，适合把命令执行、检查客户端和运行设置保持为可替换策略，同时避免 domain 层依赖 yt-dlp/FastAPI。[Python typing.Protocol](https://docs.python.org/3/library/typing.html#typing.Protocol)

## 2. 重构前成本

一个平台的变化点散落在：

- 506 行 `provider_catalog.py` 中的平台数据、URL regex 和工厂；
- `MediaCommands._ytdlp_base()` 中按平台 key 判断的动态参数；
- 命令装配中重复的 Profile 匹配、URL 规范化和下载参数；
- 193 行错误分类器中按命令字符串反推平台；
- 570 行 `MediaRunnerService` 中混合的任务编排、检查补全和封面网络访问。

这会让已有 extractor 的新平台仍需修改多个核心文件，并容易产生 inspect/download 参数漂移。

## 3. 当前目标结构

| 变化原因 | 唯一扩展点 | 模式 |
| --- | --- | --- |
| 新平台和能力声明 | `provider_catalog_*.py` 的 `ProviderProfile` | Strategy + Registry |
| 分享 URL 规范化 | `provider_normalizers.py` 的纯函数 | Strategy |
| 平台固定/运行参数 | Profile 的 `command_args` / `runtime_command_args` | Strategy |
| inspect/download 命令形态 | `YtDlpCommandBuilder` | Builder |
| stderr 到稳定错误 | 有序 `FailureRule` | Chain of Responsibility |
| metadata 补全顺序 | `RunnerInspectionPipeline` | Template Pipeline |
| 任务、会话和制品交付 | `MediaRunnerService` | Facade / Orchestrator |

`ProviderRegistry.prepare()` 每个操作只生成一次 `ProviderRequest`，其中同时保存原始安全 URL、规范化请求 URL和版本化 Profile。会话、检查、正式媒体和 probe sample 都消费同一个对象，避免平台重复识别和上下文漂移。

## 4. 接入门禁

新增公开平台的最小完成定义：

1. Profile key、version、hosts、capabilities、access mode 和 canary suite 完整且唯一。
2. URL normalizer 是纯函数；拒绝非单视频 path，不能接收用户 yt-dlp 参数。
3. 使用固定引擎完成 metadata 和 media canary；Registry 登记本身不代表 verified。
4. 私有、会员、地域、DRM、多条目或直播边界返回稳定错误，不降级到 Generic 或其他账号。
5. 回归现有 YouTube、TikTok、X 完整媒体路径以及 Runner/API readiness。

因此，平台专用 operator runner 不是普通公开平台接入步骤。只有产品明确需要并获准处理某种授权上下文时，才单独设计会话与权益隔离；它不能作为 extractor 适配失败的补丁。
