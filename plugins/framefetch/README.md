# FrameFetch Codex 插件

该插件在 Codex 中注册 `framefetch` MCP。MCP 进程初始化时会探测当前用户的
FrameFetch Local Agent；未运行时会在本机自动拉起，并通过仅监听
`127.0.0.1` 的随机端口通信。

当前工具：

- `framefetch_agent_status`：自动拉起并返回 Agent、Codex、Claude Code 状态；
- `framefetch_agent_doctor`：重新执行 Codex/Claude Code 安装与登录诊断；
- `framefetch_agent_start`：显式启动 Agent；
- `framefetch_agent_stop`：停止当前用户的 Agent。

Agent 状态目录权限为 `0700`，包含随机访问令牌的 endpoint 文件权限为
`0600`。插件不读取、复制或返回 Codex/Claude Code OAuth 凭据。

## 本地开发安装

从仓库根目录执行：

```bash
codex plugin marketplace add .
codex plugin add framefetch@framefetch-dev
codex plugin list
```

安装完成后，在新的 Codex 任务中调用 `framefetch_agent_status`。也可以直接
验证 Agent：

```bash
python3 plugins/framefetch/scripts/framefetch_agent.py doctor
python3 plugins/framefetch/scripts/framefetch_agent.py stop
```

当前发行包使用 Python 3 标准库，无额外运行时依赖。Codex App 自动注册与
拉起链路已实现；业务分析任务提交、设备配对和服务端授权将在后续协议版本
中接入。
