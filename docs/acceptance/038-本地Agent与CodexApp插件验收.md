# 038 本地 Agent 与 Codex App 插件验收

## 1. 当前结论

本机控制面和 Codex 插件自动拉起链路已通过代码级、本机安装和 Codex App
界面验收。设备配对、业务任务执行和独立签名发行尚未实现，因此 038 整体仍
处于进行中。

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
| Codex App 插件页显示已安装插件 | 通过 | [`02-plugin-installed.png`](038-agent-browser/screenshots/02-plugin-installed.png) 显示 `FrameFetch Dev` 与 `FrameFetch` 插件卡片 |
| Codex App 新任务可调用插件工具 | 通过 | [`05-status-result.png`](038-agent-browser/screenshots/05-status-result.png) 显示 Agent PID `2317`，Codex/Claude 均为 `ready`，来源为 `framefetch` |
| Codex App 可停止并重新拉起 Agent | 通过 | [`06-stop-result.png`](038-agent-browser/screenshots/06-stop-result.png) 显示停止成功；后续状态调用得到新 PID `22633` |
| Codex App 可显式停止 Agent | 通过 | 最终 `framefetch_agent_stop` 返回 `stopped: true`、`wasRunning: true`；后续 MCP 重连仍会按设计自动拉起 Agent |
| Codex App 页面运行时错误 | 通过 | `agent-browser errors --json` 返回空数组；控制台只有 Codex App 自身路由与 Statsig 警告 |

## 3. 不构成通过的范围

- 当前 `ready` 只证明官方 CLI 已安装且认证状态命令成功，不证明真实模型请求
  已执行，也不证明 FrameFetch 分析任务完成。
- 当前源码发行依赖 `python3`；尚未完成 Windows Codex App 和签名二进制验收。
- 未实现 FrameFetch 设备配对、任务领取、报告回传和远程撤销。
- Codex App 使用 `app://` 自定义协议；`agent-browser record start` 在创建录制上下文
  时因 `net::ERR_ABORTED` 失败，本轮以可访问性快照、页面文本和截图作为证据。

完整的浏览器实机记录见 [`038-agent-browser/README.md`](038-agent-browser/README.md)。

## 4. 038 完成条件

只有设备配对、服务端 lease、Codex/Claude 真实分析、取消恢复、签名安装包及
全新设备安装全部通过后，038 才能标记完成。每项必须记录目标操作系统、插件
版本、Agent 版本、服务端版本和不含凭据的结果证据。
