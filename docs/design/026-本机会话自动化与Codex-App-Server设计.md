# 026 本机会话自动化与 Codex App Server 设计

- 状态：Implemented
- 日期：2026-08-29
- 对应需求：`docs/prd/026-本机会话自动化与Codex-App-Server需求.md`

## 1. 结论

本机运行时只保留两个明确的长期边界：

1. Provider Session Broker 自管隔离、持久化的 Chrome Profile，从官方元宝页面自动读取当前 Web 认证状态，最小化并原子轮换微信视频号 Session Secret。用户不执行导出命令，也不复制或粘贴 Cookie。
2. AI Worker 通过 Codex App Server 的 stdio JSONL 协议执行每个分析任务。每个任务创建临时 thread 和 turn，完成后关闭进程，不依赖永久 WebSocket 或跨任务连接。

Cookie 是会话凭据，不是长连接。长期空闲不会导致本机“连接断裂”；平台主动撤销登录或要求扫码属于新的身份验证挑战，系统必须明确进入 `login_required`，不能伪造为可自动绕过的 Cookie 刷新。

## 2. Session Broker

Broker 是浏览器会话生命周期的唯一所有者：

- 本机启动脚本自动注册并启动受监督进程。
- 微信视频号使用 Broker 专属、仓库外的 Chrome Profile；Broker 只监听回环 CDP，不调试或复制默认 Chrome Profile。
- 进程从元宝当前 Web 认证状态生成 Runner 所需的最小会话，不依赖已经废弃的浏览器 Cookie 命名；其他 Provider 仍按 allowlist 最小化浏览器 Cookie。
- Secret 使用同目录临时文件、`0600` 权限和原子替换；Runner 只读挂载 Provider 目录。
- 状态文件只记录 `starting | ready | login_required | degraded`、更新时间和无敏感诊断，不记录 Cookie、浏览器路径或账号。
- 临时读取失败保留最后一个有效 Secret；确认登录缺失时状态转为 `login_required`。
- 微信登录页只由 Broker 的隔离 Chrome 自动打开。首次扫码或 MFA 若由平台强制触发，必须由账号本人完成；隔离 Profile 会持续保留，之后不存在人工 Cookie 操作。
- Runner 启动不读取会话 Secret；只有实际 Provider 操作才校验快照。因此一个 Provider 待登录不会拖垮 Runner 进程或 API readiness。

## 3. Codex App Server

Codex 适配器直接实现官方 App Server 生命周期：

```text
spawn stdio app-server
  → initialize / initialized
  → thread/start(ephemeral)
  → turn/start(outputSchema)
  → item/completed...
  → turn/completed
  → parse final agentMessage
  → terminate process group
```

关键约束：

- 使用 stdio 而非实验性 WebSocket，避免监听端口、鉴权和空闲连接恢复问题。
- thread 必须 `ephemeral=true`，每个分析调用独立，禁止跨任务复用上下文。
- 使用现有 `video_analysis` permission profile；工作区外不可读、指定目录外不可写、网络工具关闭、approval 为 `never`。
- 视频分析只启用项目自带的 `video_observer` MCP；剧本任务不启用 MCP。
- 最终结果只接受 `turn/completed` 前最后一个 `agentMessage`，并执行字节上限、JSON 解析和现有领域校验。
- 超时、取消、协议错误或子进程退出都终止整个进程组，不遗留 App Server 或 MCP 子进程。

## 4. 失败语义

- App Server 不可启动或协议握手失败：`analysis_cli_unavailable`。
- 本机 Codex 未登录：`analysis_cli_not_authenticated`。
- turn 返回限流、额度、沙箱或 Schema 错误：沿用现有稳定错误分类。
- Provider 会话尚未可用：Broker 保持运行并报告 `login_required`；对应下载请求 fail closed，API 与其他 Provider 保持 ready。

## 5. 非目标

- 不自动输入密码、绕过二维码、MFA、验证码或平台风控。
- 不把 Chrome Profile、Keychain、Codex Home 或 OAuth Token 挂载到容器；Broker 专属 Profile 只留在宿主机状态目录。
- 不保留 `codex exec` 兼容路径，不同时维护两套 Codex 协议。
- 不建设跨机器 App Server、远程 WebSocket 网关或共享多租户会话。
