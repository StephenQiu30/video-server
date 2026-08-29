# 016 LangChain 与 DeepSeek 视觉分析服务调研

- 日期：2026-08-29
- 目标：保留服务端本机 Codex App Server 默认线路，同时为 C 端 Web 服务增加不依赖客户端电脑的可选 DeepSeek 视觉分析能力。

## 1. GitHub 与官方资料结论

1. [`langchain-ai/langchain`](https://github.com/langchain-ai/langchain/blob/master/libs/partners/deepseek/langchain_deepseek/chat_models.py) 的 `ChatDeepSeek` 继承 OpenAI 兼容聊天模型，支持自定义 Base URL 和结构化输出；当前 `langchain-deepseek` 1.1.0 的模型 Profile 标记 `deepseek-v4-flash-vision-exp` 支持图片输入，但不支持原生视频输入。
2. [DeepSeek Vision 官方指南](https://api-docs.deepseek.com/guides/vision/)要求在 user message 中按顺序提供 `image_url` 内容块，支持 base64 内联图片；当前视觉模型不接收视频或音频。因此“把 MP4 路径交给模型”不是有效实现，服务端必须先生成图像证据。
3. [DeepSeek Responses API 官方指南](https://api-docs.deepseek.com/guides/responses_api/)与 LangChain 的 OpenAI 兼容适配说明表明，文本和图片可以进入同一结构化调用，但结果仍要由服务端 Schema 和领域 parser 复核。
4. 社区项目 [`karminski/deepseek-v4-flash-vision-exp-video-input-best-practice`](https://github.com/karminski/deepseek-v4-flash-vision-exp-video-input-best-practice) 的可复现实验显示 GIF 可能只观察到首帧，按时间排序的 JPEG 序列才是可靠输入形态。该项目只作为工程实践证据，不替代官方能力声明。
5. [`vllm-project/vllm`](https://github.com/vllm-project/vllm/blob/main/docs/models/supported_models.md) 可用 OpenAI 兼容接口托管 DeepSeek-VL2 等开源视觉模型，但这会引入 GPU、模型权重、容量和独立推理集群运维，不适合作为本项目默认线路。
6. LangChain 的 [GHSA-2g6r-c272-w58r](https://github.com/langchain-ai/langchain/security/advisories/GHSA-2g6r-c272-w58r) 涉及旧版 `langchain-openai` 在图片 URL token 计算中的 SSRF 风险。项目显式要求 `langchain-openai>=1.1.9`，并且只把当前任务产生的 base64 图片交给模型，不让模型或用户提供外部图片 URL。

## 2. 方案比较

| 方案 | 默认免 Key | C 端通用 | 视频证据 | 运维复杂度 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 只保留本机 Codex | 是 | 依赖部署主机登录 | App Server 自主观察 | 低 | 保留为默认 |
| C 端浏览器直接调用 DeepSeek | 否 | Key 会下发客户端 | 客户端处理不稳定 | 低 | 否决 |
| DeepSeek Key 写 `.env` | 否 | 每次切换需改部署配置 | 服务端可截图 | 中 | 否决 |
| Web Profile + Worker LangChain | 默认线路仍免 Key | 管理员集中配置 | 服务端顺序 JPEG | 中 | 采用 |
| 自托管 vLLM/DeepSeek-VL | 可控 | 是 | 服务端顺序 JPEG | 高 | 后续可选基础设施 |

## 3. 当前决策

- `local-codex` 继续由当前态数据库默认插入并保持激活；没有第三方 Profile 时不需要任何额外配置。
- 第三方 Endpoint、模型和 Key 通过 `/admin/ai-providers` 管理。Key 使用现有 Fernet 记录绑定加密，只在分析 Worker 内存中解密，不进入前端响应、日志、命令参数或第三方 AI `.env`。
- DeepSeek 只允许 API Key 和当前官方视觉模型 `deepseek-v4-flash-vision-exp`，避免选择文本模型后产生“任务运行但看不到画面”的假可用状态。
- Worker 使用 FFmpeg 在当前任务工作区均匀抽取 JPEG，按毫秒时间戳与图片交错发送。上限为 64 帧、4 MiB/图和 24 MiB 原始图片总量；不提取音频或字幕。
- 图片以内联 base64 发送，不创建公共截图 URL，不允许任意远程图片，不依赖 C 端用户电脑、Chrome、扩展、Cookie 或长期浏览器连接。
- 显式启用的 DeepSeek 失败时不静默切换回 Codex，避免未经管理员选择把内容发送给另一个数据处理方。失败只影响分析任务；下载、导入、文件和历史服务继续可用。

## 4. 实现映射

- `AiProviderEngine.DEEPSEEK` 与数据库约束表达 Web 可配置线路；默认行仍为 `local-codex`。
- `LangChainDeepSeekAnalyzer` 复用视频分析、剧本分析、全局汇总、术语表和分块改写端口。
- `DeepSeekFrameExtractor` 使用受监督 FFmpeg 子进程和现有工作区资源监控。
- `ConfiguredAnalyzerResolver` 按 `profile.key + updated_at` 在任务边界热切换，不要求重启 API 或 Worker。
- 生产验收仍需要一枚获授权的真实 DeepSeek Key；仓库自动化只证明协议、脱敏、顺序、资源上限和失败收敛，不伪造真实视觉结果。
