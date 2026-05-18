## Why

当前首页已从功能页到展示页的体验过于杂乱，缺少一致的转化叙事；同时项目已进入页面优化阶段，需要一版“iOS 风格蓝白简约”落地页，明确提高首屏清晰度、降低认知负担并强化 CTA 路径。

核心问题是：用户看到首页后难以快速理解产品主路径（解析 → 任务管理 → 转化动作），且当前视觉噪音不利于品牌统一。该优化可在不改变核心下载能力前提下，快速提升产品入口体验和可用性。

## What Changes

- 重构 `/` 首页为完整 SaaS Landing Page（Hero、核心价值、社会证明、FAQ、定价/终端 CTA）。
- 全面统一配色与排版风格为蓝白主色系，并采用更清晰的信息层级，减少不必要装饰。
- 优化顶栏导航与锚点结构，形成从首页到功能区、FAQ 与下载工作台的轻量入口链路。
- 补充落地页结构与可访问性测试，要求首屏 CTA、触达尺寸、focus-visible 与 `prefers-reduced-motion` 覆盖。
- 增加文档与验收闭环：将 plan、验收标准、review 证据沉淀到 `docs`，并完成 OpenSpec 验收与归档。

## Capabilities

### New Capabilities
- 本次不引入新的功能能力项。

### Modified Capabilities
- `frontend-landing-page`: 首页能力从“基本展示”升级为“完整 SaaS 落地页体验”（完整结构区块、统一信息层级、蓝白简约 iOS 风格、CTA 与可访问性约束）。

## Impact

- 代码范围：
  - `apps/web/src/pages/LandingPage.tsx`
  - `apps/web/src/components/layout/Header.tsx`
  - `apps/web/src/index.css`
- 质量与验证范围：
  - 新增/更新测试：`apps/web/tests/landing-page.structure.test.mjs`、`apps/web/tests/landing-page.a11y.test.mjs`
  - 文档：`docs/04-执行计划/04-落地页重构实施计划.md`、`docs/05-测试验收/04-落地页验收标准.md`、`docs/05-测试验收/05-落地页UI评审.md`
- 无外部 API 或后端接口变更。
