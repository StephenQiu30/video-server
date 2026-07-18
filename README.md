# video-server

`video-server` 是正在重新设计的视频下载与内容提取服务端仓库。

## 当前状态

- 旧产品设计、PRD、Plan 和 Acceptance 已清除。
- 5 份服务端 Design 已确认，5 份对应 PRD 已进入可规划状态，5 份执行 Plan 已就绪。
- 当前尚未开始业务实现，也没有 Acceptance 结果。
- 当前没有业务源码、依赖、测试、migration、schema、fixture 或业务运行配置。
- 仓库只保留项目治理文件与文档分类骨架。

## 重新设计门禁

后续工作固定遵循：

`Design → PRD → Plan → Acceptance`

当前文档链已经推进到 [执行 Plan](docs/plans/README.md)。只有在用户明确要求开始实现后，才按依赖顺序执行 Ready Plan；实现完成并通过验证后再创建 Acceptance。

## 项目规范

本仓库按 [stephen-codex](https://github.com/StephenQiu30/stephen-codex) 当前 `main` 整理：

- `AGENTS.md`：长期协作、交付与 Git 规则。
- `AGENTS.local.md`：本仓库边界与重新设计门禁。
- `WORKFLOW.md`：Symphony/Linear 编排契约。
- `.codex/`：Agent 角色与核心流程。
- `docs/`：正式文档分类骨架。
- `.github/`：PR 模板与基础 CI。

文档入口见 [`docs/README.md`](docs/README.md)。当前不提供安装、运行或部署命令。
