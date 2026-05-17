## Why

1. 登录后顶部导航栏和移动端菜单仍然显示“登录”和“立即开始”，导致用户无法确认当前登录账号信息，影响用户体验。
2. 任务的 AI 洞察报告（包含内容深度总结与 Mermaid 逻辑脑图）在原有弹窗（Dialog/Modal）中展示时，受到全局 DialogContent 组件 CSS 类中 `sm:max-w-sm` 属性的限制，被严重挤压成一条细窄 of 区域，排版混乱且超长 Mermaid 图表完全无法识别。需要设计为全新的详情展示页面，并支持在工作台直接跳转。

## What Changes

- **修改**：在全局头部导航中，如果用户已登录，则隐藏“登录”和“立即开始”按钮，并展示用户头像、展示名称及优雅的玻璃拟物化下拉菜单（支持展示个人信息、跳转工作台、退出登录）。
- **修改**：在移动端导航菜单中同步支持已登录用户的账号信息展示与退出登录逻辑。
- **新增**：新增独立且美观的“AI 洞察详情页” `/workbench/task/:id`，用于全宽、高清晰度展示特定任务的“内容深度总结”（Markdown 格式）及“逻辑视觉地图”（Mermaid 脑图），并支持 PDF 导出和一键复制等创作者功能。
- **修改**：工作台的任务列表“AI 洞察”按钮点击后不再开启受限的弹窗，而是平滑跳转至新的详情页面。
- **修复**：修改 Dialog 弹窗的限制，或通过显式覆盖类名来确保全局 Dialog 可以在需要时以正确的尺寸渲染，解决潜在的弹窗挤压问题。

## Capabilities

### New Capabilities
无

### Modified Capabilities
- `user-auth`: 增加在前端头部展示已登录用户信息、获取 `/api/auth/me` 的接口调用及退出登录状态清理逻辑。
- `frontend-workbench-ui`: 将 AI 洞察从原有弹窗交互重构为全新独立路由页面交互，并在卡片 and 布局中支持对已登录状态的响应。
- `video-ai-intelligence`: 在独立页面全屏状态下优化内容深度总结和 Mermaid 逻辑地图的呈现与渲染。

## Impact

- 涉及前端文件：
  - `apps/web/src/App.tsx` (添加用户状态获取、头部导航下拉菜单及路由注册)
  - `apps/web/src/pages/Workbench.tsx` (移除 Dialog 依赖，调整 AI 洞察按钮逻辑为路由跳转)
  - `apps/web/src/pages/TaskDetail.tsx` (新页面：用于承载完整的 AI 洞察报告和导出、复制成果)
- 无需修改后端 API，目前 `/api/auth/me` 及 `/api/tasks/{task_id}` 接口功能完备，可直接使用。
