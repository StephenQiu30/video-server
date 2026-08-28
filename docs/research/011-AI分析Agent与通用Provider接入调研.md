# 011 AI 分析 Agent 与通用 Provider 接入调研

- 日期：2026-08-13
- 结论：采用“宿主机 CLI Agent + 项目内 Provider Profile”，不修改用户全局 CLI 配置，不把宿主机登录态复制到容器。

## 1. 问题定位

现有 AI 分析不是 API 容器内的一段同步逻辑，而是宿主机上的 `analysis-worker`：它消费 RabbitMQ、下载完整视频制品，再调用 Codex CLI 或 Claude CLI。API 只有在数据库中读到兼容且未过期的 Agent 心跳时才允许创建分析任务。

本次故障的直接原因是 Agent 进程退出后没有被系统服务托管，心跳过期，因而页面得到 `analysis_unavailable`。同时，旧实现启动时固定选择 CLI，主动清除继承环境中的 API Key，只支持本机 OAuth 登录，无法安全接入自定义模型服务。

## 2. 一手资料结论

### 2.1 Codex

- Codex 官方支持 ChatGPT 登录与 API Key 两类认证；本机账号模式可以继续复用 `codex login`，无需项目保存 Key。[Authentication](https://learn.chatgpt.com/docs/auth)
- Codex 自定义 Provider 支持 `model_provider`、`base_url`、`env_key` 与 `wire_api`；当前自定义 Provider 的协议值只有 `responses`。官方明确不建议把 bearer token 直接写进配置，优先使用环境变量引用。[Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)
- App Server 提供账户、模型、结构化输出和事件能力；当前实现已用临时 stdio thread 取代 `codex exec`，不保留第二套 Codex 协议。[Codex App Server](https://learn.chatgpt.com/docs/app-server)

### 2.2 Claude Code

- Claude Code 的非交互模式会优先使用 `ANTHROPIC_API_KEY`；`ANTHROPIC_BASE_URL` 可将采样请求路由到代理或网关。[Environment variables](https://code.claude.com/docs/en/env-vars)
- Anthropic 官方网关文档认可通过 base URL 与凭据对接统一网关，但模型名仍需显式配置。[LLM gateway configuration](https://docs.anthropic.com/en/docs/claude-code/llm-gateway)
- 本机 OAuth 凭据由 Claude Code 自己管理；项目不读取或复制 `.credentials.json`。[Authentication](https://code.claude.com/docs/en/team)

### 2.3 CC Switch 可借鉴与不可照搬的部分

CC Switch 的 Provider 预设、名称/Endpoint/Key/模型字段、当前线路切换、模型探测和故障转移提供了成熟的交互参考。[Provider quick start](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/1-getting-started/1.4-quickstart.md) [Add Provider](https://github.com/farion1231/cc-switch/blob/main/docs/user-manual/en/2-providers/2.1-add.md)

本项目只借鉴以下产品模型：

1. 内置“本机登录”默认项，用户无需填写 Key。
2. 自定义项只要求名称、执行引擎、Endpoint、模型与 Key。
3. 明确显示当前启用线路，切换后下一任务生效。
4. 后续可增加预设、`/v1/models` 探测、延迟测试与故障转移。

不照搬以下实现：

- 不覆盖 `~/.codex/auth.json`、`~/.codex/config.toml` 或 `~/.claude`。
- 不把 Key 放进 deep link、浏览器存储、日志或 CLI 参数。
- 不采用 OAuth 反向代理把一个产品的订阅登录转换给另一个产品。
- 不依赖 CLI 全局配置热更新；分析任务使用项目数据库的当前 Profile 构造一次性进程环境。

## 3. 方案比较

| 方案 | 本机免 Key | 跨平台 | Secret 边界 | 自恢复 | 结论 |
| --- | --- | --- | --- | --- | --- |
| 把分析 Worker 放进 Docker | 难，需复制登录态与宿主机工具 | 一致 | 登录态进入容器 | Compose 可恢复 | 否决 |
| 每次手工运行 Worker | 是 | 是 | 良好 | 无 | 仅调试 |
| 修改用户全局 CLI 配置 | 是 | 是 | 易污染其他终端与项目 | 与进程无关 | 否决 |
| 宿主机常驻 Agent + 项目 Profile | 是 | 是 | Key 加密且按任务注入 | 系统服务重启 | 采用 |
| 自建统一 AI Gateway | 是 | 是 | 最强集中治理 | 服务端 HA | 后续阶段 |

## 4. 决策

本期采用宿主机常驻 Agent：Windows 使用当前用户的计划任务，macOS 使用 LaunchAgent，Linux 使用 systemd user service。Agent 启动后先校验当前 Profile、CLI、FFmpeg、数据库与消息队列，再写入心跳。

Provider Profile 存于 PostgreSQL，最多一个 `is_active=true`。API Key 使用项目现有 Fernet 主密钥加密，并用 `ai-provider:<profile-key>:` 前缀做领域和记录绑定。Worker 只在领取任务时解密当前 Profile，把唯一需要的 Key 注入子进程环境；子进程结束后环境随进程销毁。

## 5. 后续演进

1. Provider 预设：OpenAI、Anthropic、常用兼容网关只填 Key。
2. Agent 回报当前 Provider、CLI 版本、诊断错误与最后成功时间。
3. 在 Agent 侧执行模型列表探测和最小结构化输出测试，避免 API 容器直接访问任意 Endpoint。
4. 多线路优先级、熔断与失败转移。
5. 团队部署时引入独立 AI Gateway、Secret Manager 与按用户/项目配额。
