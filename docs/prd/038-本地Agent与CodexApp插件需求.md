# 038 本地 Agent 与 Codex App 插件需求

## 1. 用户目标

用户安装 FrameFetch Codex App 插件后，无需手工编辑 MCP 配置即可发现本机
FrameFetch 工具。插件应自动尝试启动本机 Agent，并明确显示 Codex、Claude
Code 是可用、需要登录、未安装还是诊断超时。

## 2. 本期范围

### R1 插件发行

- 仓库提供可验证的 `.codex-plugin/plugin.json`、`.mcp.json`、Skill 和本地市场
  清单。
- 安装插件后由 Codex 自动注册 `framefetch` stdio MCP。
- MCP 提供 Agent `status`、`doctor`、`start`、`stop` 四个工具。

### R2 本地 Agent

- Agent 可独立启动，且不依赖 FrameFetch 后端、数据库、队列或对象存储。
- Agent 仅监听 `127.0.0.1` 随机端口，使用当前用户私有 endpoint 和随机令牌。
- 并发 MCP 初始化不会持续拉起多个 Agent；不可达的 endpoint 可自动恢复。
- macOS、Linux 和 Windows 的状态目录规则明确；Python 入口本身使用标准库。

### R3 Codex 与 Claude Code 连接诊断

- 通过 `codex --version`、`codex login status` 判断 Codex 状态。
- 通过 `claude --version`、`claude auth status --json` 判断 Claude Code 状态。
- 不读取认证目录，不返回邮箱、组织、令牌或原始命令输出。

## 3. 非功能要求

- MCP 启动预算 10 秒，Agent 就绪预算 6 秒，单个 CLI 诊断预算 5 秒。
- 所有本机 HTTP 请求必须鉴权；未鉴权请求返回 `401`。
- 停止 Agent 后 endpoint 最终清理；异常遗留 endpoint 在下次启动时恢复。
- 插件和 Agent 版本独立于服务端版本；本机 API 使用显式 `v1`。

## 4. 暂不纳入本期

- FrameFetch 账号登录和设备配对；
- 从服务端领取分析任务、上传结果和查询报告；
- Agent 二进制签名、公证、自动更新和 Windows 安装器；
- 通过 Agent 直接调用 API 模型。API 模型仍按 037 由服务端统一 AI 执行策略
  管理。
