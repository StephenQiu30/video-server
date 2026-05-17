## Context

当前系统中，用户登录状态已通过本地 `localStorage` 的 `auth_token` 字段存储，并通过 Axios 请求拦截器自动在请求中附加 Authorization 头。然而：
1. 全局顶部导航栏（在 `apps/web/src/App.tsx` 中定义）未对接后台当前用户查询接口 `/api/auth/me`，不管用户是否登录都依然渲染“登录”和“立即开始”两个链接，导致无法在 UI 上直观看到已登录的账号信息。
2. 任务列表的 AI 洞察在原有 Dialog/Modal 中展示，由于 Dialog 样式中存在 `sm:max-w-sm` 样式规则，在桌面大屏上整个 Dialog 容器被强制限制在 384px 宽，使得 Markdown 文档和 Mermaid 视觉大图严重挤压变形，用户体验极差。

## Goals / Non-Goals

**Goals:**
- 在前端 App 顶部导航对接 `/api/auth/me` 接口，对于已登录用户优雅渲染用户头像和具有玻璃拟物化美感的下拉菜单。
- 支持在下拉菜单中进行一键退出登录（清除 token 并跳转）。
- 新增独立的 AI 洞察详情页 `/workbench/task/:id`，用于在宽屏高清晰度下全屏展示 Markdown 深度总结及 Mermaid 脑图。
- 改造任务列表卡片中的“AI 洞察”按钮，使其不再触发弹窗，而是平滑跳转至新的详情页面。
- 确保整个重构在视觉上极其高端华丽，符合“Premium UI/UX”的设计规范。

**Non-Goals:**
- 不涉及后台数据库表结构的修改或 API 的变更（目前 API 功能完全满足前端逻辑）。
- 不对除了工作台和新详情页之外的其他页面做重构。

## Decisions

### Decision 1: 独立路由详情页 `/workbench/task/:id` 替代原弹窗
- **Rationale**: 任务的“内容深度总结”可能非常长，且 Mermaid 图表横向空间要求很高。即使采用宽弹窗，在大尺寸或多节点脑图下仍然显窄。设计为一个全新独立的详情页，可利用 100% 页面宽度，支持更加优雅的网格布局、侧边栏布局、PDF 导出和一键复制等创作者功能。
- **Alternatives Considered**: 
  - *方案 B: 修改全局 Dialog 为大尺寸弹窗。* 缺点是弹窗在大屏下依然占用主视图空间，不支持页面 URL 直接分享/书签收藏，且在移动端非常不友好。

### Decision 2: 在 AppHeader 层结合 React Query 实现响应式 UserDropdown
- **Rationale**: 利用 React Query 管理全局的 `currentUser` 状态，当用户退出登录或登录成功后，能够平滑过渡，并避免频繁请求后台。在 App 根路由层做渲染，确保在所有页面中导航栏状态均是实时、准确的。
- **Alternatives Considered**:
  - *方案 B: 使用原生 Context。* React Query 本身已自带缓存和状态机制，无需引入额外的 Context/Zustand 导致架构过度设计，符合 MVP 简洁原则。

## Risks / Trade-offs

- **Risk**: 用户第一次打开 Workbench 时可能会因为后台网络延迟产生头像展示延迟。
  - *Mitigation*: 增加优雅的骨架屏（Skeleton）或默认占位头像，在数据加载过程中保持流畅的视觉过渡。
- **Risk**: Mermaid 在重新渲染或切换路由时可能会有缩放问题。
  - *Mitigation*: 在 `TaskDetail.tsx` 中采用稳定的组件容器包装 Mermaid 图表，并在外层提供水平和垂直双方向的滚动条或自动适应容器宽度。
