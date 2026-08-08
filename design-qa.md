# Design QA — Ant Design Pro 默认参数收敛

## Evidence

- 用户问题截图：`/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-5aad106a-5435-4af0-a7a2-87d39c7ee13f.png`
- 最终桌面端：`/Users/stephenqiu/Desktop/StephenQiu/Video/video-server/dogfood-output/design/antd-pro-defaults-desktop-viewport.jpg`
- 最终移动端：`/Users/stephenqiu/Desktop/StephenQiu/Video/video-server/dogfood-output/design/antd-pro-defaults-mobile-viewport.jpg`
- 问题截图与实现对照：`/Users/stephenqiu/Desktop/StephenQiu/Video/video-server/dogfood-output/design/antd-pro-defaults-comparison.jpg`
- 验收状态：`/?design=inspection`，实时解析 `https://www.bilibili.com/video/BV1D6u86fETf/`。

## Findings

- 未发现待处理的 P0、P1 或 P2 视觉问题。
- 已删除浅蓝 Hero、胶囊标签、超大标题、自定义控件高度、自定义圆角和主题 token 覆盖。
- ProLayout 使用 Fluid 内容宽度和非固定页头；输入框、按钮、Typography、ProCard、Radio 与 PageContainer 均使用组件默认尺寸。
- 页面仅保留 Ant Design 默认容器层级以及真实封面所需的媒体遮罩，没有新增装饰性背景色、阴影或渐变。
- 桌面与 390 × 844 移动端首屏无水平溢出，格式列表在窄屏下回落为单列。

## Interaction And Data Checks

- 真实 Bilibili 封面已完整加载：2560 × 1440，来源为后端返回的 `data:image/jpeg;base64,...`。
- 8 个格式均可访问，切换第二个 1080P Radio 后 checked 状态正确，再恢复默认格式成功。
- 页面展示真实标题、时长、平台、媒体 ID、编码和帧率信息。
- 浏览器控制台只有 React 开发工具提示和 HMR 连接日志，无 warning 或 error。

## Verification

- Biome lint、格式检查与 TypeScript typecheck 通过。
- 29 个 Vitest 测试全部通过。
- Next.js 生产构建通过。
- `npm run dev` 已恢复 Next.js 默认 3000 端口；本项目旧 8000 监听已关闭。

final result: passed
