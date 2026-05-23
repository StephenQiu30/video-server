# MVP Issue-PR 矩阵（video-server）

用于记录后端仓库与双仓库拆分阶段的任务链路，确保 Issue 与 PR 一一对应、按顺序可追踪。

## PR 提交顺序

| 顺序 | PR | Base -> Head | 类型 | 关闭/关联 Issue | 说明 |
|---|---|---|---|---|---|
| 1 | https://github.com/StephenQiu30/video-server/pull/31 | server-baseline-e0 -> server-pr-01-docs | docs | #2, #3, #4, #21, #22, #23, #24, #25, #30 | 后端 MVP 文档、架构边界与验收门禁 |
| 2 | https://github.com/StephenQiu30/video-server/pull/32 | server-pr-01-docs -> server-pr-02-impl | feat | #5, #6, #7, #8, #9, #10, #11, #12, #13, #14, #15 | API-only 与平台适配核心实现 |
| 3 | https://github.com/StephenQiu30/video-server/pull/33 | server-pr-02-impl -> server-pr-03-test | test | #16, #17, #18, #26, #27, #29 | API 契约、适配器与权限边界测试 |

## 核对规则

1. PR 号顺序即为合入顺序建议；每个 PR 到位后才能进入下一阶段。
2. Issue 关闭原则：
   - 该 PR 明确实现或验证对应 Issue 的验收标准后，Issue 可直接关闭。
   - 若出现阻塞性问题，保持 Issue 打开并在 PR 评论记录阻塞项。
3. 测试 PR 不应替代代码实现；每个阶段结束前保留命令输出快照。

## 备注

- 该矩阵用于 MVP 级别执行追踪，若后续迭代需增加 Issue，可按同构建增补。
