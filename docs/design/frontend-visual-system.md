# 前端视觉系统

当前实现标准由根 [design.md](../../design.md) 统一维护。

2026-09-18 按用户要求切换为官方实现优先：Next.js 官方工程规范、pnpm、shadcn radix-nova / neutral / Phosphor。旧方案中的自定义无边框基础控件、自定义 variant 和固定颜色要求已取消。页面继续通过排版与留白组织，控件使用官方边界和交互。

全局主题在 frontend/src/app/globals.css；官方组件在 frontend/src/components/ui。验收见 [design-qa.md](../../design-qa.md)。本文件不再重复维护平行主题和组件规范。
