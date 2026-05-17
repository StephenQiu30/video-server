## 1. 顶部导航与登录状态展示

- [x] 1.1 在 `App.tsx` 中提取 `AppContent` 子组件，使其嵌套在 `Router` 中并能使用路由 and 查询 Hooks。
- [x] 1.2 在 `App.tsx` 中集成 React Query 的 `useQuery` 来获取 `/api/auth/me` 接口。
- [x] 1.3 设计并编写已登录用户的头部 UserDropdown 组件，实现玻璃拟物化美感的悬浮卡片及头像、展示名、邮箱展示。
- [x] 1.4 在 UserDropdown 中实现退出登录的交互（清理 `auth_token` 缓存并刷新状态）。
- [x] 1.5 在 `App.tsx` 的移动端导航中对接已登录状态，优雅展示用户详情及退出登录按钮。

## 2. 独立 AI 洞察详情页实现

- [x] 2.1 创建全新的页面组件 `apps/web/src/pages/TaskDetail.tsx`。
- [x] 2.2 在 `TaskDetail.tsx` 中对接 `/api/tasks/{id}` 接口，获取特定任务的详情。
- [x] 2.3 设计极致精美的任务页头部，展示视频标题、时长、平台来源及高清视频封面。
- [x] 2.4 在 `TaskDetail.tsx` 中以 Markdown 渲染 `ai_summary` 总结，支持优雅的代码与排版样式。
- [x] 2.5 在 `TaskDetail.tsx` 中以 `Mermaid` 脑图组件全宽渲染逻辑脑图，配备精美的边框和合理的溢出滚动机制。
- [x] 2.6 在页面底部或顶部集成功能操作区（“导出 PDF” 和 “复制成果”）。
- [x] 2.7 在 `App.tsx` 中注册详情页路由 `/workbench/task/:id`。

## 3. 工作台与最终整合

- [x] 3.1 修改 `Workbench.tsx`，将“AI 洞察”按钮的弹窗交互移除，改为路由跳转至新创建的详情页 `/workbench/task/{id}`。
- [x] 3.2 移除 `Workbench.tsx` 中无用的 AI Modal / Dialog 相关多余代码与状态。
- [x] 3.3 进行本地打包测试与验证，确保页面不存在任何严重的排版变形与样式挤压。
