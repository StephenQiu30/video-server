## Context

当前前端 `apps/web` 已完成 Vite + React + Tailwind + shadcn 基础架构，首页落地页已有基础能力但风格与结构不完整。本次目标是对现有实现进行视觉、信息架构与可访问性收敛，不涉及下载能力接口、鉴权与后端模型。

关键约束：
- 不引入新后端依赖；仅改动前端代码与样式。
- 保持页面可用语义与基础路由不变（`/`、`/workbench`、`/auth`）。
- 以“蓝白 iOS 极简”风格为优先，避免复杂装饰与高饱和色块。

## Goals / Non-Goals

**Goals:**
- 形成完整落地页结构：`hero`、`features`、`proof`、`pricing`、`faq`、`final-cta`。
- 统一色彩、字体、卡片与按钮规则，确保触达区域、焦点反馈、锚点导航可用。
- 增补静态结构测试与可访问性测试，形成红绿测试证据。
- 产出 OpenSpec proposal/specs/design/tasks 及可归档验收文档。

**Non-Goals:**
- 不引入或修改下载任务 API。
- 不做视觉回归图像化自动化（暂不纳入本次 scope）。
- 不调整工作台内部核心流程与权限体系。

## Decisions

1. **Decision: 使用现有 Tailwind 设计代替新增组件系统**
   - Why：目前页面已依赖 shadcn，新增组件引入代价高且容易破坏样式一致性。
   - Alternative：重写为纯 CSS 或 CSS-in-JS，但会放大迁移成本。
   - Decision: 保持现有 Tailwind class + 全局 CSS 变量。

2. **Decision: 以“固定区块清单”为交付标准**
   - Why：避免“结构可变但缺失关键区块”的体验碎片化问题。
   - Alternative：按文案优先不固定锚点会增加后续验收歧义。
   - Decision: 强制保留锚点命名与 CTA 节点。

3. **Decision: 测试采用静态白盒 + 可访问性断言并与现有脚本兼容**
   - Why：不引入 E2E 重依赖即可快速形成可复现红绿反馈。
   - Alternative：先上 Playwright 全链路，但当前需求优先快交付。
   - Decision: 维持 `node:test` 结构化文本匹配，后续扩展可直接追加交互测试。

## Risks / Trade-offs

- [Risk] 仅有静态测试可能遗漏运行时交互问题 → **Mitigation**: 在验收文档记录人工交互验证清单。
- [Risk] 已有旧式样式文件（如 `App.css`）可能保留历史 token → **Mitigation**: 在风险列表记录为下一迭代任务，不阻塞本次归档。
- [Risk] CTA 与布局文本依赖文案策略可能与产品文案演进冲突 → **Mitigation**: 通过非目标边界明确排除文案大规模改版。

## Migration Plan

- **发布方式**: 直接替换首页与头部组件文件，前端热重载可见。
- **回退策略**: 若出现严重样式问题，可回退上述文件到 commit 前版本，并恢复 `landing-page` 与 `Header` 中的稳定区块。
- **灰度建议**: 先在测试环境查看桌面与移动端断点，确认导航锚点、CTA 与无障碍样式后再上线。

## Open Questions

- 是否将 `proof` 区块由纯文本口碑改为真实用户反馈（外部数据源）？
- 是否需要将 `pricing` 统一对齐后续付费墙和配额能力？
