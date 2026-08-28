# 026 本机会话自动化与 Codex App Server 需求

- 状态：Implemented
- 日期：2026-08-29
- 对应设计：`docs/design/026-本机会话自动化与Codex-App-Server设计.md`

## 1. 用户价值

启动本机服务后，微信视频号 Cookie 的发现、过滤和轮换由系统自动完成；AI 分析使用本机已经登录的 Codex App Server。用户不需要维护 Cookie 文件，也不会因一条长期闲置连接断开而失去下载或分析能力。

## 2. 功能需求

### FR-026-01 Cookie 自动化

- 微信视频号受控路由启用时，本机启动自动启动 Session Broker。
- Broker 自动管理隔离 Chrome Profile，从官方页面认证状态生成并验证 Provider 最小 Secret，不依赖人工发现 Cookie 名。
- 不提供手工 Cookie 文本输入、复制、粘贴或普通业务 API 上传入口。
- 平台要求首次或重新扫码时，由 Broker 的隔离 Chrome 自动打开官方登录页并明确报告登录待完成。

### FR-026-02 长期运行

- Broker 由本机服务管理器监督，异常退出可重启。
- Cookie 轮换失败不得破坏最后一个有效原子快照；状态不得只依赖进程存在。
- Provider 尚未登录时 Runner 与 API 仍须 ready；凭据只在对应 Provider 操作边界校验。
- 日志与状态不得包含 Cookie 值、账号、完整浏览器路径或认证响应。

### FR-026-03 Codex App Server

- Codex 分析必须使用 App Server `initialize → thread/start → turn/start → turn/completed` 协议。
- 每次调用使用临时 thread 和 stdio transport，不复用空闲连接。
- 支持结构化 `outputSchema`、现有视频观察 MCP、超时、取消、资源上限和错误分类。
- 删除 `codex exec` 当前态实现与文档，不保留双轨。

## 3. 验收指标

- 启动脚本不要求用户运行 Cookie 导出命令。
- Cookie 缺失、轮换、临时失败和恢复均有稳定单元/契约测试。
- Codex App Server 正常、协议错误、失败 turn、超时及无效输出测试通过。
- 后端 lint、类型检查与测试通过；真实本机 App Server 冒烟通过。
