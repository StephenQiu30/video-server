# 037 统一 AI 执行与 OpenRouter 接入设计

日期：2026-09-17。状态：代码与确定性验证完成，真实付费模型验收待完成。

## 决策

复用 VideoAnalyzer、ScreenplayAnalyzer、ScreenplayRewriteAnalyzer 三个策略端口。CLI 与 API 是执行适配器，不改变分析任务、结果校验、报告和租约协议。注册工厂按 engine 显式选择构造函数，拒绝未知引擎；禁止用默认 else 误选 Claude。

本次实现管理员配置的 API 执行闭环：OpenRouter、OpenAI Chat Completions 兼容服务与已有 DeepSeek。Codex/Claude 的 host_login 和 CLI 自定义 API 模式保留原本语义。API 模式无需安装 Codex/Claude；仍由现有分析 Worker 执行，仍需要媒体工具。用户设备配对、独立客户端发行和 Codex 插件属于后续交付，不能把宿主机 Worker 当作已完成的用户客户端。

## 必要模式

- 策略：应用层分析端口隔离任务编排与执行方式。
- 适配器：CLI、LangChain DeepSeek、Chat Completions 把外部协议归一为已有结构化分析结果。
- 注册工厂：唯一装配点创建运行时，配置校验与注册集合保持一致。
- 组合：API 分析器共用提示词、抽帧、限额和结果处理；不复制 DeepSeek 分析流程，不建立无业务用途的继承树。

## OpenRouter 参考与边界

官方依据：[模型目录](https://openrouter.ai/docs/api/api-reference/models/get-models)、[结构化输出](https://openrouter.ai/docs/guides/features/structured-outputs)、[Provider 路由](https://openrouter.ai/docs/guides/routing/provider-selection)。

OpenRouter 使用固定 https://openrouter.ai/api/v1 地址与 provider/model 标识。公开模型目录提供输入/输出模态、上下文长度及 supported_parameters；服务端仅读取固定公开目录，不读取管理员密钥。目录采用有界响应、超时与短期缓存，失败明确报错，不伪造模型能力。

运行时在发送媒体前检查所选模型的文本/图像输入、文本输出与 structured_outputs 能力；模型级能力只是准入条件，请求还必须携带 provider.require_parameters=true。发送 json_schema 且 strict=true；下游业务校验仍为最终准入。禁用应用内 SDK 自动重试，不配置跨模型 fallback；OpenRouter 同模型供应商 fallback 显式关闭，避免静默切换。用户额度、鉴权、超时、畸形输出、能力不支持分别映射现有错误码。

通用 OpenAI 兼容线路使用 json_object；管理员选择支持图像和 JSON 的模型，不能把简单 /models 返回的 ID 当作能力证明。未知协议不自动降级。API 响应体与结果大小均有上限、连接不跟随重定向，密钥仅保存在 Worker 内存中，错误不包含上游正文或请求头。

## 配置和产品入口

engine 新增 openrouter/openai；只允许 api_key。OpenRouter Base URL 固定；通用线路可设置 HTTPS Base URL 或本机 HTTP。保留凭据密文存储与 local-codex 保护规则。Web 管理页提供对应选择、OpenRouter 模型目录及能力说明；公开 OpenAPI 同步生成客户端。

## 与用户 Agent / 插件的关系

后续用户 Agent 通过设备身份和任务租约 API 接入，仅接收自己的任务；服务端 Secret 不下发用户电脑。本机 OAuth 与服务端 API 密钥分属各自执行节点。插件提供业务 MCP，启动桥接连接本地 Agent；MCP 与 Web 共用任务应用服务。不得把 OpenRouter 的网络路由等同于用户设备调度，也不得把本地调用再次接回插件造成递归。
