# 038 Codex App 实机验收记录

## 环境

- 日期：2026-09-17
- 工具：`agent-browser 0.33.0`
- 应用：macOS Codex App，Chromium Framework `153.0.8010.36`
- 插件：`framefetch@framefetch-dev 0.1.0`
- 项目：`Video`

## 场景与结果

| 场景 | 操作 | 可观察结果 | 结论 |
| --- | --- | --- | --- |
| 插件注册 | 打开 Codex App 的插件页 | `FrameFetch Dev` 下出现已安装的 `FrameFetch` 卡片 | 通过 |
| 首次状态调用 | 在新任务中限定只调用 `framefetch_agent_status` | Agent 自动启动，PID `2317`；Codex `0.149.1`、Claude Code `2.1.220` 均为 `ready` | 通过 |
| 停止 | 限定只调用 `framefetch_agent_stop` | 页面返回“停止成功”，Agent 从运行态进入停止态 | 通过 |
| 再次状态调用 | 再次限定只调用 `framefetch_agent_status` | Agent 自动重新拉起，PID 变为 `22633`；两个 CLI 仍为 `ready` | 通过 |
| 再次停止 | 再次限定只调用 `framefetch_agent_stop` | 页面返回 `stopped: true`、`wasRunning: true` | 通过 |
| 页面错误 | 读取 `agent-browser errors` | 返回 `errors: []` | 通过 |

Codex App 的“来源”面板在这些回复中显示 `framefetch`。这证明结果来自已安装插件
注册的 MCP，而不是任务通过 shell 直接运行脚本。

最终停止后，Codex App 的 MCP 连接在 `19:15` 再次初始化，并按插件设计自动拉起
PID `28475`。这不否定停止结果，也说明“停止”不是禁用插件；验收收尾时再次执行
本地 `stop`，3 秒后进程表中没有 Agent 服务。

## 证据

- [`02-plugin-installed.png`](screenshots/02-plugin-installed.png)：插件安装状态。
- [`03-new-task.png`](screenshots/03-new-task.png)：Video 项目中的新任务。
- [`04-prompt-ready.png`](screenshots/04-prompt-ready.png)：首个工具调用指令。
- [`05-status-result.png`](screenshots/05-status-result.png)：首次 Agent 与 CLI 状态。
- [`06-stop-result.png`](screenshots/06-stop-result.png)：首次停止结果。
- [`codex-task-transcript.txt`](codex-task-transcript.txt)：同一任务中的完整页面文本，包含重启 PID 与最终停止结果。

`exploratory/` 保留了插件页定位期间的原始截图，其中 `00-initial-capture.png`
是一次只有 `2×300` 像素的失败捕获，不作为验收证据。

## 验证边界

本轮覆盖插件可见性、MCP 工具发现、Agent 自动拉起、诊断、停止、重启和清理。
它没有执行 FrameFetch 业务分析，也没有覆盖设备配对、服务端任务租约、报告回传、
Windows 安装或签名发行。

`agent-browser record start` 会为录制创建新的浏览器上下文，并尝试导航到当前
`app://` 地址。Codex App 拒绝该导航并返回 `net::ERR_ABORTED`，因此本轮没有视频；
截图、可访问性快照和页面文本均由同一 CDP 会话采集。

控制台只出现 Codex App 自身的空路由和缺少 `workspace_id` 的 Statsig 警告，未发现
FrameFetch 插件相关错误。
