# Vercel / shadcn 页面一致性设计 QA

## 对照目标与证据

- 主要风格真值：`vercel-home-hero-reference-2026-08-09.png`。
- 分区与网格参考：`vercel-home-section-reference-2026-08-09.png`、`vercel-home-grid-reference-2026-08-09.png`。
- 业务布局基线：`vercel-refinement-baseline.png` 与方案 2 原图 `/Users/stephenqiu/.codex/generated_images/019fe595-9cfd-7e10-8cc2-ca36f82e7f0b/exec-093b654f-524e-4641-aeb6-a196aa75c23c.png`。
- 最终桌面实现：`vercel-refinement-implementation-desktop-final.png`。
- 最终同视口对照：`vercel-refinement-comparison-final.jpg`，左侧为 Vercel，右侧为帧取。
- 最终移动端实现：`vercel-refinement-implementation-mobile-final.png`。
- 检查路由与状态：`/?design=inspection`，开发态演示用户、Bilibili 链接已解析、1080P 已选中。

## 本轮页面一致性复核

- 2026-08-09 在同一次比较输入中打开 `vercel-home-hero-reference-2026-08-09.png` 与最新 `/?design=inspection` 浏览器截图；最新首页已删除装饰性英文眉题，继续保留 Vercel 式浅色画布、大留白、发丝线和低容器感。
- 1280×720 首页实测 `documentElement.clientWidth = scrollWidth = 1265`；Header `.page-shell` 与 `main.content-shell` 均为 1200px，左右边界同为 32.5px。首页 H1 为 56px，正文色为 `rgb(29, 29, 31)`。
- 1280×720 404 页实测 `clientWidth = scrollWidth = 1280`；Header 与 main 均为 1200px，左右边界同为 40px；H1 为 32px/38.4px，`404` 元数据为 muted 灰色。
- 认证页实测 PageShell 为 1200px、左右边界 40px，H1 为 32px/38.4px；Card 的可见 border、圆角和阴影均为 0，不再形成页面级外框。
- 标准内页统一复用 `PageHeader`：390px 为 28px，`sm` 起为 32px；全局唯一页面外框在桌面保留 24px gutter、390px 保留 16px gutter。首页 Hero 是唯一 38.4–56px H1 例外，详情与空页面使用同一 28/32px 标准。
- 源码已删除 `Public media workflow`、`Available formats`、`Download status`、`AI analysis` 及“任务记录 / 账户设置 / 系统管理 / 欢迎回来 / 开始使用”等装饰性眉题；证据编号、章节时间、平台 Badge、头像和装饰图标均改为中性色。Apple 蓝只保留在操作、链接、焦点、选择、当前步骤和加载状态。
- 本轮受保护内页由共享 PageHeader、页面级 CSS、54 项 Vitest 与 production static build 回归；浏览器中的开发态预览身份在跨文档导航后不会保留，因此 Acceptance 仍不把“全路由逐页截图与 axe”标为完成。

## 视口与归一化

- Vercel 参考和桌面实现截图均为 1265×712 像素，同尺寸水平拼接为 2530×712，不做缩放。
- 桌面浏览器视口为 1280×720，页面 `clientWidth = scrollWidth = 1265`，无页面级横向溢出。
- 移动浏览器视口为 390×844，截图内容宽 375，页面 `clientWidth = scrollWidth = 375`，无页面级横向溢出。
- 本轮比较 Vercel 的视觉语言，不复制其营销内容或黑色品牌主色；帧取保留任务型产品的信息顺序和 Apple 蓝主操作。

## Findings

最终对照无可操作的 P0、P1 或 P2 差异。

- 排版：Geist 的 56px / 500 首屏标题、紧凑行高与大留白，和 Vercel 当前首页的视觉节奏一致；装饰性 Mono eyebrow 已删除，中文在 390px 下自然折为两行。
- 画布与层级：背景为 `#FAFAFA`，Header 为 64px sticky 细线结构；主内容依靠留白、`1px` 分隔和真实媒体画面组织，不使用大面积阴影或卡片套卡片。
- 颜色：主操作使用 `#0071E3`，焦点环为 `#007AFF`；Card、Popover、Muted、Border、Input 与半径均来自语义 token。
- 组件：页面实际使用官方 shadcn / Radix 的 Card、Table、Sheet、Tooltip、Avatar、Field、InputGroup、Item、Empty、Pagination、AlertDialog、AspectRatio、Select、RadioGroup、Switch、Dialog、DropdownMenu 和 Tabs 组合。
- 内容：格式区只展示契约真实提供的分辨率、封装、编码与帧率；不虚构文件大小、发布日期或其他后端未返回字段。
- 响应式：桌面 5/7 双栏在移动端按“格式 → 下载 → 预览”收敛为单列；Header 使用 Sheet 导航，触控目标、字段和主按钮保持可达。
- 交互：浏览器实测链接清空、RadioGroup 方向键选择、账户菜单打开/Escape 关闭、移动 Sheet 打开/Escape 关闭；焦点返回触发控件。
- 导航：桌面 Header 与移动 Sheet 均提供“视频解析”和“下载历史”；真实页面已从历史页回到 `/`，验证互斥 `aria-current`、移动 Sheet 导航后关闭与 390px 无横向溢出。
- 取消安全：下载和 AI 分析的取消操作均通过 AlertDialog 二次确认，取消弹窗不会调用 API，确认后才执行原动作。
- 运行时：最终页面日志没有产品代码 error；检查期间仅出现开发态 HMR 重载提示。生产静态构建不包含 Next.js 开发工具。

## QA 历史

1. 初始实现偏 Apple 消费级：纯白背景、38px 标题、72px 大圆角输入和自定义组合较多。
2. Pass 1 改为 Vercel 式 `#FAFAFA` 画布、56px 标题、64px Header、细线网格，并接入官方 shadcn 组件；发现当前 Radix 运行时使用 `data-state="checked"`，而最新 registry 样式使用 `data-checked`，导致选中 Radio 与 Switch 状态不可见。
3. 最终修复将官方组件的状态选择器适配到实际 Radix `data-state`，并复核 Radio 计算样式为 `rgb(0, 113, 227)`、键盘切换后第二项 `aria-checked="true"`。

## Implementation Checklist

- [x] 捕获并打开 Vercel 首页 Hero、产品分区和网格参考。
- [x] 同一 1265×712 尺寸合并参考与实现并逐项比较。
- [x] `#FAFAFA`、Geist、Apple 蓝、细线 Header 和无重阴影层级。
- [x] 官方 shadcn / Radix 组件源码与语义 token。
- [x] 390×844 检查，无横向溢出。
- [x] 关键鼠标、键盘、菜单、Sheet、Radio 和 AlertDialog 交互。
- [x] Header、main 与 footer 统一 1200px 页面边界；标准内页 H1 统一为 28/32px。
- [x] 删除非交互蓝色眉题；保留操作、链接、焦点、选择、当前步骤与状态色。
- [x] 页面级 Card 视觉改为无 border/ring/shadow，保留输入、分隔和浮层等功能边界。
- [x] lint、format、TypeScript、54 项单元测试和 Next.js 静态导出构建。

## Open Questions

- 无阻塞问题。Vercel 参考使用营销型三栏叙事，帧取按任务完成顺序保留居中解析入口与结果双栏，这是有意的产品映射而不是视觉遗漏。

final result: passed
