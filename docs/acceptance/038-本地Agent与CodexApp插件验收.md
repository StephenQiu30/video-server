# 038 本地 Agent 与 Codex App 插件验收

## 1. 当前结论

本机控制面和 Codex 插件自动拉起链路已通过代码级与本机安装验证。设备配对、
业务任务执行和独立签名发行尚未实现，因此 038 整体仍处于进行中。

## 2. 已通过门禁

| 门禁 | 结果 | 证据 |
| --- | --- | --- |
| 插件清单可被官方 validator 接受 | 通过 | `validate_plugin.py plugins/framefetch` |
| MCP 初始化自动启动 Agent | 通过 | `test_mcp_initialization_starts_agent_and_exposes_lifecycle_tools` |
| MCP 暴露四个生命周期/诊断工具 | 通过 | 同上 |
| Agent 仅使用 loopback 随机端口 | 通过 | `test_local_agent_requires_token_and_uses_private_state` |
| 无令牌请求被拒绝 | 通过 | 同上，HTTP `401` |
| 状态目录与 endpoint 为私有权限 | 通过 | macOS/POSIX 测试 `0700` / `0600` |
| Codex/Claude 状态可区分 | 通过 | `test_diagnostics_distinguish_ready_login_required_and_missing` |
| Claude 身份字段不进入诊断结果 | 通过 | 同上 |
| 插件不导入后端且不继承服务密钥 | 通过 | `test_plugin_distribution_is_backend_and_secret_independent` |
| 仓库市场安装并出现在插件列表 | 通过 | `framefetch@framefetch-dev`，版本 `0.1.0`，enabled |
| 安装包可启动 MCP 并连接真实 CLI | 通过 | Codex `0.149.1`、Claude Code `2.1.220` 均返回 `ready` 后正常停止 |
| 新 Codex 任务可发现并调用 MCP 工具 | 通过 | `codex exec -m gpt-5.6-sol` 调用 `framefetch_agent_status`，返回 Codex/Claude 均已就绪 |

## 3. 不构成通过的范围

- 当前 `ready` 只证明官方 CLI 已安装且认证状态命令成功，不证明真实模型请求
  已执行，也不证明 FrameFetch 分析任务完成。
- 单元测试中的 MCP 往返证明本地协议，不替代 Codex App UI 中的新任务验收。
- 当前源码发行依赖 `python3`；尚未完成 Windows Codex App 和签名二进制验收。
- 未实现 FrameFetch 设备配对、任务领取、报告回传和远程撤销。

## 4. 038 完成条件

只有设备配对、服务端 lease、Codex/Claude 真实分析、取消恢复、签名安装包及
全新设备安装全部通过后，038 才能标记完成。每项必须记录目标操作系统、插件
版本、Agent 版本、服务端版本和不含凭据的结果证据。
