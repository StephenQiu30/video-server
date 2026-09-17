# 037 统一 AI 执行与 OpenRouter 接入需求

- 管理员可选择本机 Codex/Claude、DeepSeek、OpenRouter、OpenAI 兼容服务。
- API 用户只配置地址、Key、模型，不安装 CLI；OpenRouter 提供实时模型目录和视觉/结构化能力信息。
- 视频、剧本分析与剧本改写使用相同已有业务入口；错误不改变所选线路，不泄露 Key。
- 已有配置和默认本机 Codex 不被自动迁移或覆盖。
- 本切片不包含用户设备发行、配对、插件安装和原生 Anthropic/Responses 直连接口；它们复用本设计的策略端口。
