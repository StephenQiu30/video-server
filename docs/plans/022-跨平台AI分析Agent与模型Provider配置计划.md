# 022 跨平台 AI 分析 Agent 与模型 Provider 配置计划

- 状态：In Progress（内部实现与自动化契约完成，仅跨 Provider 与跨平台实机验收待完成）

## 阶段 1：领域与持久化

- [x] 新增 AI Provider 领域模型与管理员服务。
- [x] 新增当前状态 schema、ORM、默认本机 Codex Profile 和唯一活动索引。
- [x] 使用 Fernet 和领域前缀绑定加密 Provider Key。
- [x] 增加只写凭据的 OpenAPI 管理接口。

## 阶段 2：Worker 动态解析与恢复

- [x] 新增 `ConfiguredAnalyzerResolver`，按任务读取活动 Profile。
- [x] Codex 通过 `env_key + responses` 注入自定义 Provider。
- [x] Claude 通过 `ANTHROPIC_API_KEY/BASE_URL` 注入。
- [x] 保留本机 OAuth 预检与最小环境隔离。
- [x] 队列、心跳和恢复组件使用指数退避自恢复。

## 阶段 3：跨平台 Agent

- [x] Windows 当前用户计划任务，登录启动并失败重启。
- [x] macOS LaunchAgent，`RunAtLoad + KeepAlive`。
- [x] Linux systemd user service，`Restart=always`。
- [x] 提供 `doctor/install/status/uninstall/run` CLI。
- [ ] 在三台真实系统完成安装、重启与卸载验证。

## 阶段 4：管理端

- [x] 新增 `/admin/ai-providers` 路由与管理员导航。
- [x] 当前执行链路与 Agent 在线状态分离展示。
- [x] 新增响应式新增/编辑 Dialog、启用与删除动作。
- [x] OpenAPI 生成客户端，不手写协议类型。
- [x] 完成 390×844 与桌面真实浏览器视觉验收。

## 阶段 5：验证

- [x] 后端单元、集成与全量测试通过。
- [x] 前端 lint、typecheck、测试与 build 通过。
- [x] 本机 Codex Profile 完成一次真实视频分析。
- [ ] 测试 API Key Profile 完成一次真实视频分析并确认脱敏。
- [x] 更新 Acceptance 实测证据与状态。

## 剩余外部门禁

截至 2026-08-14，Key 留空/轮换、管理 API 脱敏、活动 Profile 热切换、stale worker fail-closed、子进程参数隔离以及三平台服务命令契约均已有自动化证据。当前工作区没有可用于验收的真实 API Key，也没有 macOS/Linux 实机，因此只剩以下不可由仓库内测试替代的任务：

1. 使用获授权的 API Key Profile 完成一条真实视频分析，审计任务结果、Agent 普通日志和进程快照均不含 Key。
2. 在 macOS 实机完成 LaunchAgent install、登录启动、异常重启、status 与 uninstall。
3. 在 Linux 实机完成 systemd user service install、登录启动、异常重启、status 与 uninstall。

完成上述证据前，Design/PRD/Plan/Acceptance 不得改为归档状态，也不得绕过归档器门禁。
