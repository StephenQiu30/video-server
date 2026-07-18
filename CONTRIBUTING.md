# Contributing

`video-server` 按 `Design -> PRD -> Plan -> Acceptance -> Implementation` 推进。

## 贡献门禁

1. 先阅读 `AGENTS.md`、`AGENTS.local.md`、`WORKFLOW.md` 和 `docs/README.md`。
2. 需求必须映射到已接受 PRD 的 Requirement ID，不能在实现中引入隐性范围。
3. 只有 `status: ready` 的 Plan 可以实施，每次只推进一个依赖就绪的 Plan。
4. Acceptance 必须先冻结验收项，再通过失败测试驱动最小实现。
5. 完成时逐项附上命令、响应、测试或运行证据；未验证项保持 `failed` 或 `blocked`。

## 当前允许的实现

首个候选是 Plan 001：URL 安全与来源策略、异步元数据解析、格式归一化、任务查询和事件恢复。只有独立审查通过并将其标为 `ready` 后才允许实现。

以下能力必须等待对应 Plan 就绪：

- 实际下载、FFmpeg 合流和对象存储。
- AI 转录、总结和思维导图。
- PDF 渲染、历史库和数据生命周期自动化。
- DRM、登录态、付费墙、地区限制或下载禁用绕过始终不在范围内。

## 工程要求

1. 遵循 `AGENTS.md` 的提交类型、TDD 顺序、文件体量和 PR 门禁。
2. 依赖版本、运行方式和验证命令必须进入仓库，不依赖口头约定。
3. 不引入 `.planning`、临时状态文件、兼容旧实现的双轨结构或未清理生成物。
4. 不提交凭据、完整签名 URL、Cookie、令牌、用户媒体或转写正文。
