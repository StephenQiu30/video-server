# Contributing

`video-server` 按 `Design -> PRD -> Plan -> Acceptance -> Implementation` 推进。

## 贡献门禁

1. 先阅读 `AGENTS.md`、`AGENTS.local.md`、`WORKFLOW.md` 和 `docs/README.md`。
2. 需求必须映射到已接受 PRD 的 Requirement ID，不能在实现中引入隐性范围。
3. 只有 `status: ready` 的 Plan 可以实施，每次只推进一个依赖就绪的 Plan。
4. Acceptance 必须先冻结验收项，再通过失败测试驱动最小实现。
5. 完成时逐项附上命令、响应、测试或运行证据；未验证项保持 `failed` 或 `blocked`。

## 当前允许的实现

当前只实施已就绪的 Plan 000：邮箱身份、PostgreSQL UUID owner/数据库会话、可恢复邮件 intent、Redis/outbox、MinIO 对象 Saga 与恢复；Plan 001 继续等待 Plan 000 完成。

以下能力必须等待对应 Plan 就绪：

- URL 来源解析、实际下载和 FFmpeg 合流。
- AI 转录、总结和思维导图。
- PDF 渲染、历史库和数据生命周期自动化。
- DRM、登录态、付费墙、地区限制或下载禁用绕过始终不在范围内。

## 工程要求

1. 遵循 `AGENTS.md` 的提交类型、TDD 顺序、文件体量和 PR 门禁。
2. 依赖版本、运行方式和验证命令必须进入仓库，不依赖口头约定。
3. 不引入 `.planning`、临时状态文件、兼容旧实现的双轨结构或未清理生成物。
4. 不提交凭据、完整签名 URL、Cookie、令牌、用户媒体或转写正文。
