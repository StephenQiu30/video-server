# 首页方案 1 与页面导航验收

日期：2026-09-25。本文件记录本次验收事实，视觉规范仍以 design.md 为唯一来源。

## 对比对象

- 视觉目标：用户选定方案 1，移除标签行右侧的快捷操作提示。
- 原图：/Users/stephenqiu/.codex/generated_images/01a0d2d6-7506-7f42-a66e-6c6dd6424684/exec-007888d9-64b5-4130-baab-9df96bb69d38.png（1681 × 936）。
- 实现：http://localhost:8101/，已登录、亮色、链接解析空输入。
- 实现截图：/tmp/framefetch-option1-qa/home-desktop.png（1425 × 792）；CSS 视口 1440 × 800，设备 DPR 2，浏览器截图工具输出已缩放。对比按图像各自画幅比例归一，不将截图密度和滚动条差异当成 CSS 尺寸差异。
- 原图与实现截图在同一次视觉输入中对照。全图中的标题、紧凑 Tabs、输入行和导航可读，无须额外放大裁切。

## 对比结论

- 首页采用左对齐的紧凑 Tabs、整行输入与外置按钮，标签行右侧没有提示；内容与导航共用左右边界，保留彩色 Logo。
- 字体与控件不按生成图等比放大：遵循用户要求和 design.md，使用现有 PageHeader 的 30px 桌面标题、14px 说明及官方 Tabs 字号/默认底面，输入与按钮保持共享 56px 高度。生成图的字体、图标及 Tabs 视觉仅作构图参考，不将其转成新的自定义组件皮肤。
- 三个模式均在同一行、同一垂直位置显示输入/选择器和操作按钮；桌面浏览器实测高度全部为 56px。
- 本次渲染对比未发现需要继续修复的 P0/P1/P2 布局问题；没有增加装饰卡片、背景或阴影。

## 导航统一与实测

根因：BackLink 同时带默认 32px 高与 min-height 36px；各页面分别添加 mb-4、mt-8、pt-10，操作日志又使用外层 gap，导致不同页面的返回入口和内容距离不一致。

修复：通过 PageNavigation 统一组合官方 ghost Button 和导航行，清除页面的重复边距；加载和错误视图同步使用。当前业务页为返回导航，不伪装成路径面包屑。

在 1440/1920px 桌面视口实测，以下页面导航高度均 32px、导航顶部 y=96、与后续页头/主体内容间距均 24px：

- 下载记录、剧本文档、平台状态、系统操作日志。
- 个人资料、AI 服务、下载分析、文件管理、平台目录、用户管理。
- 下载详情加载占位与实际内容（截图：/tmp/framefetch-option1-qa/download-detail.png）。

管理员页实测数据：/tmp/framefetch-option1-qa/navigation-measurements.json。

## 交互与响应式

- 首页三个 Tabs 实际切换通过；原有 56px 入口尺寸保持一致。
- 390 × 844 窄屏亮色和深色无页面横向溢出；文件选择器长文字截断，不挤压操作按钮。
- 手机下载记录返回行 32px，顶部 y=88，内容间距 24px；点击返回后回到首页并保留已选模式。
- Command+K 可打开快捷操作，仍显示链接、本地视频、剧本文档三个入口；Escape 关闭。
- 桌面和手机明暗主题可用，已恢复浅色；控制台本轮检查无 error。
- 截图：/tmp/framefetch-option1-qa/home-mobile.png、home-mobile-dark.png、home-desktop-dark.png、history-mobile-dark.png。

## 工程检查与范围

- pnpm format:check、pnpm lint（含 TypeScript）、pnpm test：91 个文件、479 项测试全部通过。
- pnpm build 通过；Docker frontend 镜像构建并更新本地服务成功。
- 本次没有创建解析/上传任务，不将布局验证当成新的媒体下载或上传集成验收。
- 所有页面级返回入口已迁移；404 操作区保留内联 BackLink，共用官方按钮尺寸，不承担页头导航布局。
- 未逐个触发网络故障和所有详情数据状态；这些分支的导航实现共用组件，已有测试通过。

final result: passed
