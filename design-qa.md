# 方案 3 无边框重设计 QA

## 对照目标与证据

- 视觉来源：Vercel Home（2026-08-09 捕获）与用户确认的方案 3 无边框稿。
- Vercel 参考：`/Users/stephenqiu/.codex/visualizations/2026/08/09/019fe657-3556-7102-a4d8-f0f95698076b/product-design/vercel-home-reference.png`。
- 方案 3 真值：`/Users/stephenqiu/.codex/generated_images/019fe657-3556-7102-a4d8-f0f95698076b/exec-6ad65a6b-a139-48c1-a789-730a53116807.png`。
- 最终桌面实现：`/Users/stephenqiu/.codex/visualizations/2026/08/09/019fe657-3556-7102-a4d8-f0f95698076b/product-design/implementation-1536x1056.png`。
- 最终移动实现：`/Users/stephenqiu/.codex/visualizations/2026/08/09/019fe657-3556-7102-a4d8-f0f95698076b/product-design/implementation-390x844.png`。
- 同一比较输入：`/Users/stephenqiu/.codex/visualizations/2026/08/09/019fe657-3556-7102-a4d8-f0f95698076b/product-design/comparison-reference-left-implementation-right.png`，左侧为方案 3，右侧为最终实现。
- 路由与状态：`/?design=inspection`，开发态演示账户、媒体已解析、1080P 已选中。
- 2026-08-10 Header 比例回归：在已登录的 `/downloads/detail` 真实任务页上完成 2048px、1280px 和 390px 实时测量与可见截图检查。

## 视口与归一化

- 桌面浏览器视口覆盖为 1536×1056；浏览器可见截图为 1521×1046（扣除滚动条与浏览器捕获边缘）。
- 方案稿原图为 1487×1058。并排图为两个 1521×1058 单元格，均保持原始比例居中，不做非等比拉伸；中间使用 24px 中性分隔。
- 移动浏览器视口为 390×844，页面 `clientWidth = scrollWidth = 375`，无页面级横向溢出。
- 桌面与移动均使用同一已解析演示状态、浅色主题和同一真实预览素材。
- Header 比例回归的 2048px 视口中，Header/main 均为 `x = 328.4px / width = 1376px`；1280px 视口中均为 `x = 80px / width = 1104.8px`。Header 高度为 80px，Logo 为 28px，导航控件为 44px。
- 390×844 回归中 Header/main 均为 `x = 16px / width = 343.2px`，移动导航触发器为 44px，`clientWidth = scrollWidth = 375`。
- 2026-08-10 认证与导航响应式回归中，820×900 登录表单为 `x = 190px / width = 440px`，中心与视口中心偏差为 `0px`；390×844 登录表单为 `x = 16px / width = 358.4px`，中心偏差仅为设备像素舍入产生的 `0.2px`，两个视口均满足 `clientWidth = scrollWidth`。
- 2026-08-10 布局稳定性回归在 1280×600 复现了长短页面切换问题：修复前短 404 页右侧导航 `x = 804.2px`，长历史页 `x = 789px`，存在 `15.2px` 位移。启用稳定 scrollbar gutter 与固定账户槽后，两页 Header shell 均为 `x = 80px / width = 1104.8px`，导航均为 `x = 776.6px / width = 408.2px`，页面切换位移降为 `0px`。
- 2026-08-10 冷启动追踪进一步定位到历史页摘要只在数据返回后挂载，导致列表区域下移 64px、CLS 为 `0.0179`。摘要改为加载态与完成态共享 18px 固定槽位后，Docker 生产镜像连续两次冷加载 CLS 均为 `0`；Header 仍为 80px，页面无横向溢出。
- 2026-08-10 AI 详情页回归在 2048px 真实完成态量测：上方下载详情区与下方 AI 分析区均为 `x = 328.5px / width = 1376px`，左右边界差值均为 `0px`；下方配置态与运行态移除额外 `max-width` 后统一消费完整 `.content-shell`，页面无横向溢出。

## 最终对照结论

- 首屏结构与真值一致：导航与主体共用约 80px 内容边距、80px 无底边 Header、直接的编辑式中文标题、68px 浅灰输入带、黑色主操作、媒体与设置双栏、发丝分隔和底部事实型使用提示。
- 排版节奏一致：标题、描述、输入带和结果区的垂直起点与方案稿基本对齐；Geist、近黑文字、`#FAFAFA` 画布和小半径控件形成 Vercel Home 的克制层级。
- 无边框要求已落实：页面级 Card、筛选壳、认证壳和主要控件不使用可见描边或重阴影；只在表格行、内容分区、双栏和 Footer 保留必要的发丝线。
- 业务差异均为有意映射：最终实现展示 API 实际返回的 4 个完整格式，不复制稿中后端不存在的“字幕”“仅音频”“容器独立选择”和播放按钮；不虚构文件大小或精确 FPS。
- 生产数据缩略图缺失时显示明确的“封面不可用”状态；山景素材只用于 `?design=inspection` 演示，并已由 2.3 MiB PNG 压缩为约 221 KiB WebP。

## 响应式与交互验证

- 390×844 首屏自然收敛为标题、输入、主按钮、媒体和画质单列；下半屏的 4 个格式、真实元数据、创建任务与安全状态均可达。
- 移动 Sheet 可打开/关闭，包含视频解析、下载记录、个人资料与退出；Sheet 无可见边框，明暗主题跟随系统偏好。
- 响应式导航在 820px 使用移动 Sheet、在 1024px 切换为桌面导航；Sheet 保留当前页 `aria-current="page"`、内部 `overflow-y: auto`、Escape 关闭与触发器焦点恢复。1024px 实测 Logo 为 32px、品牌文字为 17px，页面无横向溢出。
- Header 账户槽在认证恢复、未登录入口和 Avatar 菜单之间固定为 88px，已登录控件为 74×44px；共享 Button 与 `asChild` 导航链接的 computed `transform` 为 `none`，transition 仅包含 `background-color, color, opacity`，按下和异步状态不再改变组件几何。
- 浏览器实测：清空链接、重新填入链接、720P/480P/1080P Radio 切换、移动菜单，以及系统明暗主题跨刷新保持。
- 直接打开登录页时已保存的深色主题能够恢复；首屏前置主题脚本与 hydration 后初始化共同避免主题缺失。
- 最终完整重载后浏览器日志没有产品代码 error；开发期曾出现的主题脚本挂载告警已修正为根 `<head>` 内的 `beforeInteractive` 脚本。

## 可访问性与契约复核

- URL 输入、RadioGroup、Select、Dialog、Sheet、DropdownMenu、Tabs、Table、Switch 和按钮继续使用 shadcn/ui + Radix 语义与键盘行为。
- 无边框控件的唯一焦点状态提高到 60% ring 对比；浅色 muted 文本、success 状态与深色 warning/destructive 状态均使用可读性更高的语义色。
- 媒体元数据保持合法 `dl > div > dt + dd` 内容模型；图片失败状态使用准确的辅助技术名称。
- 下载创建仍只提交 `inspection_id + format_id`，格式枚举使用 `balanced | quality | smallest` 的真实映射；`smallest` 显示为“体积优先”。
- 管理员编辑 Dialog 在小屏和放大场景具备视口高度上限与内部滚动；404 高度按真实 80px Header 计算。

## QA 历史

1. 初版实现采用过大的两行 Hero 和右置描述，首屏结果区低于方案稿；已改为方案 3 的单行标题、左置描述与 80px 内容边距。
2. 第一轮并排比较发现媒体画布偏高、格式选中态过重且 Footer 被推离首屏；已调整 1.86 封面比例、格式行高、透明选中表面和 Footer 间距。
3. 代码审查发现 `smallest` 映射、深色主题恢复、中间断点、状态色与焦点对比问题；均已修复并加入相应测试断言。
4. 移动复核补齐 Sheet 内主题入口、合法描述列表、生产封面失败状态、可滚动管理员 Dialog 和 72px 404 高度。
5. 最终同输入比较确认没有剩余可操作的 P0、P1 或 P2 视觉差异。
6. 下载历史页复核后将 Header 切换为与主体相同的 `.content-shell`，并把桌面顶部留白从 96px 收紧到 64px。浏览器量测在 1280px 视口得到 Header/main 同为 80px 左 gutter，在 390px 视口得到同为 16px 左 gutter、40px 顶部留白且 `scrollWidth = clientWidth`；两个视口均无框架错误层或控制台错误。
7. 首页移除没有功能绑定的 `⌘V` 占位提示；Header 与页面 metadata 改为复用既有 `logo.svg`/`logo.png` 品牌资源，Logo 由 Next.js `Image` 渲染，功能状态继续使用 Phosphor 图标；同时移除未引用的旧 Pro 图标与电竞演示 PNG，保留真实封面和 WebP 回归资产。
8. 首轮品牌密度收敛曾将字号统一为 `text-sm`；后续在 2048px 真实任务页复核发现，24px Logo、40px 导航控件与大尺寸媒体主体之间的视觉比例偏弱。
9. Header 调整为 80px，品牌 Logo 为 28px，品牌/导航文字为 15px，桌面导航控件为 44px；仍保持无边框、无阴影与 `.content-shell` 对齐。2048px、1280px 和 390px 实测均无横向溢出或对齐偏差。
10. 品牌层级后续增强为 32px Logo 与 17px 品牌文字；窄屏认证表单改为居中，完整桌面导航断点调整到 `lg`，其余宽度使用可滚动的 Radix Sheet。820px、390px 与 1024px 实测确认居中、断点、当前页语义、Escape/焦点恢复及横向溢出均通过。
11. 跨页面导航抖动定位为经典滚动条增减与认证账户控件宽度变化叠加，组件按下抖动定位为共享 Button 的 1px translate。根滚动槽、88px 账户槽与无几何位移的基础 Button 已统一收敛，并通过长短页面、认证态和浏览器 computed style 回归。
12. `agent-browser` 冷启动追踪发现历史页仍有异步摘要插入造成的残余 CLS；现以固定几何槽承载摘要/骨架，并把 Switch、Tabs 的 `transition-all` 收敛为绘制属性。注册页同时补齐无效保留域名的前置中文校验，实测不会再发出无效注册请求。
13. AI 分析区曾在配置态和运行态分别使用 `max-w-5xl` / `max-w-3xl`，导致其右边界与上方 1376px 下载详情区不一致；统一改为 `w-full` 后，2048px 真实成功态的上下区块左右边界均完全重合，32 个分镜、6 个高光和 17 个资产的长内容渲染也未产生横向溢出。

## 工程门槛

- `npm run lint`：通过。
- `npm run format:check`：155 个文件全部通过；前端换行契约已由 `.gitattributes` 固定为 LF，不再依赖开发机 Git 配置。
- `npm test`：27 个测试文件、97 项测试全部通过。
- `npm run build`：Next.js 16.3 静态导出通过，9 个业务路由与 404 均成功生成。
- Docker 启动链路：`database-init` 幂等执行并以 0 退出，API readiness 为 200，PostgreSQL、RabbitMQ、Valkey、MinIO 与 Media Runner 均健康。
- 部署后浏览器回归：历史页连续两次 CLS 为 `0`；390×844 注册页 CLS 为 `0`、无横向溢出，无效 `.invalid` 邮箱显示中文字段错误且未产生 `/api/auth/register` 请求。
- 独立前端差异审查：无剩余 P0/P1/P2；本轮发现的 2 个中等级问题均已修复。

final result: passed

## 2026-08-25 平台描述分割线与首页横向溢出回归

### 对照目标与证据

- 用户来源截图：`C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-9ecf0cac-265a-4a8f-9967-bf2841b76d5d.png`（平台状态行间分割线）与 `C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-041e8129-1f4a-40ce-8139-450db0bd1f6e.png`（首页本地视频状态的大面积留白及横向滚动）。
- `agent-browser` 修复前证据：`C:/Users/ADMINI~1/AppData/Local/Temp/video-layout-qa-20260825/screenshots/before-local-video-dev.png`；1920px 视口下 `documentWidth=2191`，页面横向溢出 271px，唯一越界元素为本地视频的隐藏文件输入，边界为 `left=271 / right=2191 / width=1920`。
- 修复后证据：`C:/Users/ADMINI~1/AppData/Local/Temp/video-layout-qa-20260825/screenshots/after-local-video-dev.png`、`after-home-mobile-light.png`、`after-home-mobile-dark.png`、`after-providers-dev.png`、`after-providers-mobile-light.png` 与 `after-providers-mobile-dark.png`。

### 修复与浏览器实测

- 本地视频文件输入继续复用共享 `Input` 组件和可访问标签，但显式收敛为 1px 的屏幕阅读器控件，并移除其可见输入框边界与内边距；1920px 和 390×844 下均得到 `documentWidth=viewportWidth`、横向溢出 0px，文件输入实测宽度为 1px。
- 平台状态列表移除外沿 `border-y` 与逐行 `border-b`，改由每行 24px 上下留白组织连续信息流。1920px 与 390×844 下，列表外沿及四条平台描述的上下边框计算值全部为 `0px`，页面横向溢出为 0px。
- 浅色画布实测为 `rgb(250, 250, 250)`，深色画布为 `rgb(10, 10, 10)`；两个主题与 reduced-motion 下均无产品控制台 error。平台状态的“返回上一步”可由可访问树定位并激活，直接访问时正确回到 `/`。
- `?design=inspection` 仅使用仓库定义的开发预览用户；平台列表数据通过 `agent-browser` 对本地开发服务器的 `/api/providers` 提供受控响应，不读取或复制用户浏览器 Cookie。

### 工程验证与 Findings

- `npm run lint`、43 个测试文件/155 项测试、Next.js production build 与 16 个静态页面全部通过；本次四个修改代码/测试文件的 Biome 格式检查和 `git diff --check` 通过。
- 全仓 `npm run format:check` 仍报告与本次改动无关的既有 `analysis-article-result-view.tsx`、`analysis-panel.tsx` 两处格式差异；本轮未顺带改动这两个文件。
- 没有剩余 P0、P1 或 P2 的分割线、留白或页面级横向溢出问题。

final result: passed

## 2026-08-25 剧本文档上传横向溢出补充回归

### 对照目标与证据

- 用户来源截图：`C:/Users/ADMINI~1/AppData/Local/Temp/codex-clipboard-59032ef3-702b-4fc5-820e-2cdc578b3062.png`；首页“剧本文档”状态出现大面积右侧空白和页面级横向滚动。
- `agent-browser` 修复前证据：`C:/Users/ADMINI~1/AppData/Local/Temp/screenplay-layout-before.png`；1920px 视口下 `documentWidth=2191`，横向溢出 271px。唯一越界元素为“选择剧本文档文件”的隐藏输入，其边界为 `left=271 / right=2191 / width=1920`。
- 修复后证据：`C:/Users/ADMINI~1/AppData/Local/Temp/screenplay-layout-after-desktop.png` 与 `C:/Users/ADMINI~1/AppData/Local/Temp/screenplay-layout-after-mobile.png`。

### 修复与验证

- 剧本文档文件输入与本地视频文件输入统一为 1px 的屏幕阅读器控件，并显式移除边框与内边距，避免共享 `Input` 的 `w-full` 把不可见控件扩展到整屏。
- 1920px 桌面视口实测 `documentWidth=clientWidth=1920`，390×844 移动视口实测 `documentWidth=clientWidth=390`；两个视口下文件输入宽度均为 1px，没有剩余越界元素或产品运行错误。
- 单元测试新增隐藏输入不保留 `w-full` 的回归断言；`npm run lint`、43 个测试文件/155 项测试、目标文件 Biome 检查与 Next.js production build（16 个静态页面）全部通过。

final result: passed

## 2026-08-17 弹层与长内容显示回归

### 对照目标与实现

- 用户来源截图：`/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-a421a301-f2e3-4a1f-987a-9c3271342da1.png`；截图中 `/documents` 的“上传剧本文档”弹窗出现内容向右溢出，长文件名被裁切。
- 实现截图：`/tmp/fanqv-upload-dialog-fixed.jpg`；截图为修复后的 `/documents` 弹窗页面视口。源图包含浏览器 Chrome 外壳且处于已选长文件状态，实施截图为页面视口且处于未选文件状态，因此本次只对弹窗内容区域做聚焦对照，不作整张截图的像素级比较。
- 源图为 2696×1740、按 2× 视网膜密度约合 1348 CSS px；实施截图为 1512×693 CSS px。

### Findings 与修复

- 修复前实测：Dialog `clientWidth=512`、`scrollWidth=566`；直接子节点宽度为 534，超过弹窗内容区 22px，导致长文件名和表单内容显示不全。
- 复用并加固官方 shadcn/Radix `Dialog`、`AlertDialog`、`Sheet` 基座：加入 `min-w-0` 和直接子节点收缩约束，避免网格/弹性子项把内容撑出弹层。
- 剧本与媒体上传表单的文件名改为最多两行换行显示，并保留完整文件名 `title`；不再依赖单行截断承载关键内容。
- 剧本分析完成态与视频分析完成态统一为全宽标题、独立操作行，避免长标题与操作按钮互相挤压。

### 浏览器实测

- 修复后弹窗：`clientWidth=512`、`scrollWidth=512`；Header 与表单宽度均为 480，未发现可见的横向内容溢出。
- 桌面端复核 `/`、`/history`、`/documents`、`/documents/detail`、`/providers`、`/account`：页面级 `body/document.scrollWidth` 与 viewport 一致；文档长预览保留局部滚动，不把页面整体撑宽。
- 本轮真实浏览器重点覆盖已登录桌面视口与弹层状态；未将本次结果扩展为完整移动端或 WCAG 合规声明。移动端布局仍由共享 `.content-shell`、`min-w-0` 与响应式 reflow 规则约束。

### design.md 对齐

- 保持共享 `.content-shell` 的连续画布和 Header/main/Footer 内容轴，没有新增 PageShell/Card 等平行视觉层。
- 继续使用项目已有的 shadcn/ui、Radix、Button、Dialog、Sheet、Item 等官方组件；本次修改集中在共享 primitive 和现有表单，不新增自定义弹窗组件。
- 长内容遵循“不裁切、必要时局部滚动、网格/弹性子项允许收缩”的规范；状态与交互仍使用现有语义组件和设计 token。

### 工程验证

- 前端完整测试：39 个测试文件、146 项测试通过。
- `npm run lint`：通过；Biome 仅报告仓库既有 `.agents/skills` 断开符号链接 warning，TypeScript 通过。
- `git diff --check`：通过。
- Docker production build：通过；`video-api` 重建后 `/health/live` 返回 `{"status":"ok"}`。

### Findings

- 在本次覆盖的桌面路由和弹层状态中，没有剩余 P0、P1 或 P2 显示问题。

final result: passed

## 2026-08-16 BasicLayout 统一应用壳回归

- 缺陷基线：应用页原先由路由和业务 View 分别创建 `main`、`.content-shell` 与 `.inner-page`，全局没有 SiteFooter；Header 与页面主体的对齐责任分散，新增页面容易复制出不同的外层宽度。
- 实现：新增 `frontend/src/components/basic-layout.tsx` 和 `site-footer.tsx`。已认证应用页现在由同一壳提供 80px Header、唯一 `main#main-content`、`flex-1` 中间内容槽和 64px Footer；Header/main/Footer 三者直接复用 `.content-shell`。
- 桌面运行态：浏览器 CSS viewport 为 1265×720（保留常驻滚动条槽），Header/main/Footer 左边界均为 `x=80px`、宽度均为 `1105px`；高度分别为 80px、576px、64px，`main` 数量为 1、全局 Footer 数量为 1。
- 移动运行态：390×844 视口的 CSS 内容宽度为 375px，Header/main/Footer 均为 `x=16px`、宽度 `343px`，Footer 高 64px，`scrollWidth=375px`，没有页面级横向溢出。
- 认证例外：登录页仍使用 `.page-shell` 双栏结构，运行态确认存在 1 个 main、0 个全局 Footer，不显示受保护应用导航壳。
- 证据截图：`/tmp/framegrab-layout-audit/01-login.png`、`/tmp/framegrab-layout-audit/02-basic-layout-404-desktop.png`、`/tmp/framegrab-layout-audit/03-basic-layout-404-mobile.png`、`/tmp/framegrab-layout-audit/04-login-after-layout.png`。
- 工程验证：39 个前端测试文件、144 项测试通过；`npm run format:check`、`npm run lint` 和 `npm run typecheck` 通过。Biome 仅报告仓库既有 `.agents/skills` 损坏符号链接警告。

final result: passed

## 2026-08-15 移动端首页视觉中心校准

### 对照目标与证据

- source visual truth：根目录 `design.md` 的共享移动网格、明确光学中心与 390×844 响应式规则，以及 `docs/design/frontend-visual-system.md` 的首页三入口规范。
- 缺陷基线：`/Users/stephenqiu/.codex/visualizations/2026/08/14/01a00156-709b-7891-838c-39184921bf40/home-mobile-before-css390x844.png`，390×844 px；修复前三入口组宽 342px、中心 `x=187px`，比 390px 内容视口中心左偏 8px。
- implementation screenshot：`/Users/stephenqiu/.codex/visualizations/2026/08/14/01a00156-709b-7891-838c-39184921bf40/home-mobile-centered-css390x844.png`，390×844 px；CSS 内容视口 390×844、DPR 1、浅色、已登录、首页“链接解析”初始态。
- desktop regression：`/Users/stephenqiu/.codex/visualizations/2026/08/14/01a00156-709b-7891-838c-39184921bf40/home-mobile-centering-desktop-1280x900.png`，1280×900 px；CSS 内容视口 1280×900、DPR 1。
- same comparison input：`/Users/stephenqiu/.codex/visualizations/2026/08/14/01a00156-709b-7891-838c-39184921bf40/home-mobile-centering-before-after.png`，左侧为修复前基线、右侧为修复后同视口同状态实现，两个 390×844 单元均未缩放或裁切。

### 全局与聚焦对照

- full-view comparison：Hero、说明、输入和主按钮保持既有左对齐编辑式层级，入口组改为占满同一 `.content-shell`；修复没有改变 80px Header、40px Hero 顶部节奏、字体、颜色、表面、圆角或下方留白。
- focused region comparison：390px 下 Header、main、H1、入口组和主按钮的中心均为 `x=195px`；三个入口宽度均为约 119px，并以 `x=16 / 135 / 255px` 连续等分到 `x=374px`，不再存在组级左偏。
- 320px 窄屏复验：修复前 `clientWidth=320 / scrollWidth=358`，入口组仍宽 342px；修复后 `clientWidth=scrollWidth=320`，入口组宽 288px、中心 `x=160px`，三个入口各 96px、44px 高。
- focused regions 已覆盖入口组、Header/main 共轴、主操作和 320px 极窄重排；页面没有图像内容或小尺寸复杂图形，因此不需要额外资产局部对比。

### 五个忠实度表面

- fonts and typography：继续使用 Geist Sans 与中文系统回退，字号、字重、行高、字距和 Hero 换行均未改变；移动标签保持 14px，不通过缩小文字解决适配。
- spacing and layout rhythm：唯一布局变化是移动端三等分入口组；`sm` 及以上恢复原有 342px 内容宽度线型 Tabs，1280px 桌面端实测 Header/main `x=80 / width=1120px` 且无横向溢出。
- colors and visual tokens：没有修改颜色、主题 token、边界、阴影或状态色；浅色捕获保持现有层级，深色继续消费未改动的同一语义 token 与结构类。
- image quality and asset fidelity：没有新增或替换图像；品牌继续使用真实 `logo.svg`，入口图标继续使用既有 Phosphor 资产。
- copy and content：标题、说明、三个入口名、输入占位和主操作文案均保持不变，没有为了布局截断、缩写或删除任务信息。

### 交互与比较历史

1. 首轮测量记录 P2 响应式偏差：390px 入口组中心左偏 8px，320px 产生 38px 横向溢出。
2. 将移动端 Tabs 改为三列满宽网格，并把每个 Trigger 的移动内边距收敛到可容纳 320px 的尺寸；`sm` 以上保留原有内容宽度与 24px 间距。
3. 后验同图比较确认 P2 已消除：390px 所有主要区域共用 `x=195px` 中心，320px `scrollWidth=clientWidth`；本地视频与剧本文档状态同样无溢出且没有 checkbox。
4. 移动 Sheet 打开时宽 304px、`clientWidth=scrollWidth=405px`；关闭后恢复 `390/390px`，焦点返回“打开导航菜单”。导航顺序仍为“首页 → 下载记录 → 剧本文档 → 平台状态”，浏览器 error/warn 日志为空。

### Findings

- 没有剩余可执行的 P0/P1/P2 差异。
- 没有遗留 P3 视觉打磨项；本轮不改变桌面信息层级或页面纵向构图。

### 工程证据

- lint/typecheck 与 format check 通过，仅保留既有 `.agents/skills` 损坏 symlink warning。
- 39 个测试文件、143 项测试全部通过；Next.js 生产构建生成 15 个静态页面。
- Compose 统一镜像重建完成，`/health/ready` 返回 200。

final result: passed

## 2026-08-15 首页统一内容入口与导航顺序

### 对照目标与证据

- 用户视觉来源：`/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-20ae7f63-7f60-4d20-ab13-8ac1d3765059.png`，3372×1942 px，用于锁定当前浅色无边框 Header、Geist 层级、中性填充面与留白节奏。
- 桌面实现捕获：`/Users/stephenqiu/.codex/visualizations/2026/08/14/01a00156-709b-7891-838c-39184921bf40/home-unified-entry-default.png`，1265×720 px；CSS 视口为 1280×720，捕获密度为 1，扣除 15px 稳定滚动条槽。
- 移动实现捕获：`/Users/stephenqiu/.codex/visualizations/2026/08/14/01a00156-709b-7891-838c-39184921bf40/home-unified-entry-390x844.png`，375×844 px；CSS 视口为 390×844，捕获密度为 1，扣除 15px 稳定滚动条槽。
- 对照状态：浅色、已登录、首页默认“链接解析”；另完成“剧本文档”激活态、390×844 移动 Sheet 和 1024×800 导航断点检查。
- 同一比较输入已同时打开用户来源、桌面实现和移动实现。来源是 `/documents` 空态而本轮实现是首页，因此只对共享 Header、token、排版与密度做忠实对照，不对两个不同业务状态做伪精确位置比较。

### 全局与聚焦对照

- 信息架构：首页在同一 Hero 下展示“链接解析 / 本地视频 / 剧本文档”，没有增加卡片、第二层导航或新路由。
- Header 聚焦对照：保留 80px 无边框 Header、32px 真实 Logo、17px 品牌文字与 15px 导航层级；桌面 DOM 中固定排列为“首页、下载记录、剧本文档、平台状态”，且只有首页带 `aria-current="page"`。
- 1024px 聚焦测量：Header 为 `x=80 / width=849`，桌面导航为 `x=375 / width=554`，`scrollWidth=clientWidth=1009`，品牌与四个导航项不碰撞。
- 390px 聚焦测量：`scrollWidth=clientWidth=375`，三个 Tabs 在一行内可读；Sheet 中前四项与桌面顺序完全一致，首页正确带 `aria-current="page"`。

### 五个忠实度表面

- 字体与排版：继续使用自托管 Geist 与中文系统回退；Hero 保留编辑式尺度、0.96 行高和紧凑字距，“把素材，带回本地。”在移动端自然换行。
- 间距与布局节奏：延续 `.content-shell`、80/32/16px gutter、发丝分隔和无 Card 内容流；剧本文档的选择与主操作在首页与本地视频使用相同的 68px 双列/移动单列几何。
- 颜色与 token：画布、前景、muted、主操作和 focus ring 全部继续消费现有语义 token，未新增一次性颜色、阴影或圆角。
- 图像与资产：没有新增装饰图像；品牌仍使用真实 `logo.svg`，导航和内容模式使用现有 Phosphor 图标，没有文本符号或 CSS 伪图标。
- 文案与内容：Hero 从只指向视频收敛为“素材”，说明文案明确列出公开视频链接、本地视频与剧本文档；安全提示同步覆盖三种来源。

### 交互、可访问性与工程证据

- 三个 Radix Tabs 可由 ArrowRight 按源顺序切换，实测从“链接解析”连续两次到达“剧本文档”。
- 剧本模式显示文件选择、权利声明和“上传并解析”；空提交返回关联的“请先选择一份剧本文档” Alert。
- 移动 Sheet 可打开、展示统一顺序并关闭；浏览器 console/error 为空。
- React/Next.js 检查确认没有新的嵌套组件定义、不必要 effect、数据瀑布或非语义点击区；两个导航表面复用相同路由和当前页语义。
- 前端门禁：lint/typecheck、format、39 个测试文件/143 项测试和 15 页 Next.js production build 全部通过；Docker 统一镜像重建并且 `/health/ready` 返回 200。

### 发现与比较历史

- 首轮同图对照没有发现可执行的 P0/P1/P2 差异。本轮只改变信息架构和文案，没有在对照后修改颜色、排版、布局 token 或资产，因此无后续 P0/P1/P2 修复迭代。
- 来源图未提供首页三模式的具体排版；实现以仓库已验收的首页 Tabs、本地视频表单和 Vercel/Geist token 为当前真值，这是有意的产品约束，不属于视觉漂移。
- 无遗留 P3 打磨项。

final result: passed

## 2026-08-13 Frontend 与 `design.md` 一致性修复

- 明确以仓库根 `design.md` 约束 Frontend，而不是反向改写规范：保留既有 Geist、语义 token、连续内容画布与 shadcn/ui + Radix 交互原语。
- 移除 Header 与移动 Sheet 中的可见主题切换器；明暗主题继续由 `next-themes` 跟随系统偏好，浅色与深色使用同一套信息层级。
- 清理认证页、账户页、任务状态、编辑器和 404 中的装饰性 eyebrow；移除认证字段、空状态和分析 KPI 中不增加任务意义的图标。
- 表头、KPI、进度、分页和普通统计值统一使用 Geist Sans + `tabular-nums`；Geist Mono 仅保留给来源键、目录键、日期时间和技术标识符。
- 空状态改为左对齐、任务特定的文字结构，不再用通用插图占位；错误、警告与操作图标仍保留语义和非颜色提示。
- 浏览器实测覆盖 1440×900 深色首页与认证页、390×844 浅色首页与移动 Sheet；桌面认证页 `scrollWidth = clientWidth = 1440`，控制台无产品代码 error。
- 新证据：`qa-output/frontend-design-md-audit-20260813/03-home-after-dark.png`、`qa-output/frontend-design-md-audit-20260813/05-home-after-mobile-light.png`、`qa-output/frontend-design-md-audit-20260813/06-mobile-menu-after-light.png`、`qa-output/frontend-design-md-audit-20260813/09-login-after-dark-desktop.png`。
- 工程门禁：format check 与 lint/typecheck 通过（仅保留既有 `.agents/skills` 断链 warning）；30 个测试文件、115 项测试通过；Next.js 生产构建与 12 个静态页面导出通过。

final result: passed

## 2026-08-13 `design.md` audit remediation

- Removed the decorative `01 / 02 / 03` eyebrows from the home hero, download task detail and both AI analysis states. Flow remains explicit through headings, actions and state content.
- Replaced “安全解析”“隐私保护” and “安全下载” with specific authorization and credential-boundary guidance that can be checked against the current validation rules and repository policy.
- Fresh desktop evidence: `/Users/stephenqiu/Desktop/StephenQiu/Video/video-server/qa-output/design-md-fix-20260813/web-home-1440.png`.
- Fresh mobile evidence: `/Users/stephenqiu/Desktop/StephenQiu/Video/video-server/qa-output/design-md-fix-20260813/web-home-390.png`.
- Browser verification at 1440×900 and 390×844 found meaningful content, no Next.js error overlay, no numbered flow labels and `scrollWidth = clientWidth` in both viewports. The H1 remained “把视频，带回本地。” and the refreshed authorization/credential footer guidance rendered in both layouts.
- `npm run format:check` and `npm run lint` passed with only the pre-existing broken `.agents/skills` symlink warning; 31 test files / 117 tests passed; the Next.js production build generated all 12 static pages successfully.

final result: passed

## 2026-08-12 无边框一致性与页头二次收紧回归

- 按 `agent-browser` dogfood 流程对首页、下载历史、下载详情缺失态、平台状态、账户、用户管理、平台目录与下载分析进行真实浏览器审查，覆盖 1440×900、390×844、浅色/深色、Radix Dialog 与 Sheet；记录并修复 3 个可复现视觉/UX 问题，详见 `dogfood-output/report.md`。
- 常规认证内页统一改为 `.inner-page`：390px 为 24px，641px 及以上为 32px；`BackLink` 到 PageHeader 固定 16px。1440px 平台目录/用户管理实测返回入口 `y = 112px`、标题 `y = 172px`；390px 实测返回入口 `y = 104px`、标题 `y = 164px`。
- 首页保留编辑式 Hero 的差异化节奏，但从移动/平板/桌面 56/64/72px 收紧为 40/48/56px；移除装饰性眉题后，标题直接占据首个内容层级，避免导航后留白吞噬首屏内容。
- 平台目录统计摘要移除上下双分隔，编辑 Dialog 的能力说明继续复用 shadcn Alert 并改为无边框 `surface` 表面；计算样式确认能力说明 `border-width = 0px`。Radix Dialog/Sheet 的遮罩、焦点圈定、Escape、焦点恢复和覆盖层边界不受影响。
- 下载任务缺失态恢复统一内页与顶部返回路径；浅色/深色桌面和 390px 页面均满足 `scrollWidth = clientWidth`，浏览器未发现产品控制台异常。
- 工程门禁：lint/typecheck 通过；format check 172 个文件通过；31 个测试文件、109 项测试通过；Next.js 生产构建与 11 个静态页面导出通过；完整 Compose 重建后 API、Media Runner、egress proxy 与基础设施健康，宿主机 AI Worker 已恢复，`/health/ready` 返回 200。

final result: passed

## 2026-08-12 内页页头密度与无边框组件回归

- 常规认证内页统一复用 `.inner-page`：390px 为 40px、641–1023px 为 56px、1024px 及以上为 64px。管理员页面原有 96px 桌面顶部留白已移除，80px Header 下不再叠加过长空档；BackLink 与共享 PageHeader 的间距统一为移动 20px、其余视口 24px。
- 1280×900 用户管理与平台目录实测 main 均为 `x = 80px / width = 1120px / top = 80px`，PageHeader 均从 `y = 212px` 开始；390×844 用户管理与平台目录 main 均为 `x = 16px / width = 358px / top = 80px`，PageHeader 均从 `y = 184px` 开始。
- 平台状态已改为共享 PageHeader，并使用 shadcn Item/ItemGroup 表达连续能力列表。AI 结果中的分镜、高光和资产同样使用 Tabs + Item/ItemGroup + 发丝 Separator，重试和时间操作统一复用 shadcn Button；逐项可见边框卡片与业务组件中的原生按钮已清除。
- 1280px 用户管理、平台目录、平台状态，以及 390px 用户管理、平台目录均满足 `scrollWidth = clientWidth`。桌面表格与移动 Item 重排、无边框填充筛选、近黑主操作和发丝分隔均正常，页面没有可见 Card/PageShell 外壳。
- 浏览器证据：`E:/StephenQiu/Video/qa-output/ui-refresh-users-1280.png`、`E:/StephenQiu/Video/qa-output/ui-refresh-users-390.png`、`E:/StephenQiu/Video/qa-output/ui-refresh-providers-1280.png`、`E:/StephenQiu/Video/qa-output/ui-refresh-providers-390.png`、`E:/StephenQiu/Video/qa-output/ui-refresh-status-1280.png`。
- 工程门禁：lint/typecheck 通过；format check 172 个文件通过；31 个测试文件、109 项测试通过；Next.js 生产构建与 11 个静态页面导出通过。`npm run openapi:check` 发现同步后的后端契约会机械改写 `analyses.ts` 的重试接口注释，生成漂移与本轮 UI 变更无关，本轮未保留该生成差异。

final result: passed

## 2026-08-12 下载分析 Radix 可视化回归

- 下载分析页继续使用无边框内容流：页面、筛选、指标、趋势和来源区均无 Card 外壳与装饰边框；仅指标列、数据表行保留必要发丝分隔，趋势绘图区使用无描边的中性实心表面。
- 7/30/90 天筛选改为单选 Radix Toggle Group；趋势图例使用多选 Radix Toggle Group，支持键盘逐项切换全部、成功、失败与取消系列；成功率和来源占比使用 Radix Progress，并保留等价精确数据表。
- 趋势图新增低对比总量面积层、末端数据点、日均任务与单日峰值摘要。桌面浅色、桌面深色和 390×844 移动端均完成真实渲染检查；系列开关高度为 44px，状态切换不改变布局几何。
- 桌面证据：`E:/StephenQiu/Video/qa-output/archive/analytics-radix-20260812/analytics-radix-desktop-final.png`；移动证据：`E:/StephenQiu/Video/qa-output/archive/analytics-radix-20260812/analytics-radix-mobile-final.png`；深色证据：`E:/StephenQiu/Video/qa-output/archive/analytics-radix-20260812/analytics-radix-dark.png`。
- 1440px 桌面与 390px 移动端均满足 `scrollWidth = clientWidth`；移动列表按 Item 摘要重排，未出现表格横向滚动。浏览器控制台仅包含开发态 React DevTools/HMR 信息，无产品代码错误。
- 当前工程门槛：lint/typecheck 通过；format check 172 个文件通过；31 个测试文件、108 项测试通过；Next.js 生产构建与 11 个静态页面导出通过。

final result: passed

## 2026-08-12 覆盖层滚动锁回归

- `agent-browser` 使用经典滚动条模式复现：根节点 `scrollbar-gutter: stable` 与 Radix 的 `react-remove-scroll` 同时补偿 15px，导致所有 Dropdown、Dialog、AlertDialog、Select 和 Sheet 触发器看起来像“按钮点击后整页抖动”。
- 根因修复以 `body` 的常驻纵向滚动条稳定长短页面切换，同时移除根节点的第二套滚动条槽位编排；未覆盖 `data-scroll-locked`，滚动锁、焦点圈定与 Escape 行为继续由 Radix 原语统一负责。
- 1440×500 下 Dropdown、Dialog、Select 打开前后 `.content-shell` 均为 `x = 80px / width = 1265px`；390×500 下移动 Sheet 打开前后均为 `x = 16px / width = 343px`。
- 浅色、深色与系统主题恢复均无布局位移；浏览器页面错误为空。

final result: passed

## 2026-08-12 异步按钮刷新稳定性回归

- `agent-browser` 在保留 15px 经典滚动条的 1262×900 环境复核 Dropdown、Dialog、Select 与普通数据刷新按钮。Dropdown/Dialog/Select 打开前后 Header 与 main 的 `x / width` 均不变，移动 390×844 Sheet 打开前后 Header shell 均为 `x = 16px / width = 343px`，因此本轮抖动并非 Radix 滚动锁补偿回归。
- 通过在浏览器内把 XHR 延迟 1 秒，稳定复现真实根因：用户管理点击搜索后，10 行 Table 被 5 行骨架替换，文档高度从 `1314px` 瞬间降至 `824px`；平台状态点击刷新后清空已有 22 行，文档高度从 `2756px` 降至 `568px`。请求返回时内容再次展开，形成肉眼可见的两次跳动。
- 用户搜索/分页、平台目录写入后回读、平台状态刷新、下载分析周期切换与刷新现统一保留已有内容；骨架只用于首次无数据加载。后台请求期间容器使用 `aria-busy`，不卸载 Table、ItemGroup、指标或图表。
- 同样的 1 秒延迟回归中，用户管理刷新期间 Table 保持 `top = 427px / height = 770px`、文档高度保持 `1314px`；平台状态列表保持 `top = 325px / height = 2399px`、文档高度保持 `2756px`。证据为 `dogfood-output/jitter/admin-users-refresh-fixed.png` 与 `dogfood-output/jitter/providers-refresh-fixed.png`。
- 工程门禁：format check 172 个文件通过；lint/typecheck 通过；31 个测试文件、111 项测试通过；Next.js 生产构建与 11 个业务/错误路由静态导出通过；Compose 重建后 readiness 返回 200。

final result: passed

## 2026-08-13 Vercel/Geist 产品规范审查

- 以根目录 `design.md` 的 Vercel 判断为基准，并按 `agent-browser` dogfood 流程审查全部前端路由；覆盖 1440×900、390×844、浅色/深色、移动 Sheet 与桌面 Radix Dialog。审查发现 2 个中等级和 1 个低等级偏差，均已修复，详见 `dogfood-output/vercel-design-audit/report.md`。
- 平台状态页只保留验证/访问状态 Badge，能力改为 Geist Sans 辅助文字与 `·` 分隔。部署后 DOM 中 22 个 Badge 对应 22 个平台状态，不再为能力额外生成胶囊；桌面和 390px 均无横向溢出。
- 管理员平台排序列，以及下载分析的任务、成功率、用户、数据量列，表头与单元格统一右对齐并使用 `tabular-nums`。浏览器 computed style 确认全部 `text-align = right`；KPI 与数值单元格使用 Geist Sans，目录键和来源键继续使用 Geist Mono。
- 缺失任务、下载历史、下载分析、平台目录和用户管理的 Empty 状态移除无独立语义的圆角图标底座；缺失任务同时移除重复“任务不可用”眉题并收紧标题前间距。浏览器复验 `empty-icon = 0`、H1 `y = 204px`、`scrollWidth = clientWidth`。
- AI 结果中的镜头属性、资产类型、评分和下载尝试次数改为普通元数据；状态、角色与可见性继续使用 Badge。根规范同时明确产品主题切换是允许的项目例外，不引入报告站 `vbg-*` 平行层。
- 覆盖层稳定性复验：1440px 深色平台编辑 Dialog 打开前后 main 均为 `x = 80px / width = 1265px`，无滚动锁位移；390×844 明暗主题平台状态页均无横向溢出，浏览器页面错误和产品控制台错误为空。
- 工程门禁：lint/typecheck 通过；format check 173 个文件通过；31 个测试文件、117 项测试通过；Next.js 生产构建与 11 个业务/错误路由静态导出通过。Compose 重建后 API、Media Runner、egress proxy 与基础设施健康，宿主机 AI Worker 已恢复，`/health/ready` 返回 200。

final result: passed

## 2026-08-14 归档前跨路由与权限复验

- 使用独立管理员与普通用户会话复验首页、下载历史、账户、用户管理、下载分析和平台目录；管理员数据页正常加载，普通用户直接访问 `/admin/users` 与 `/admin/analytics` 均被重定向回首页，账户菜单不暴露管理入口。
- 1440×900 桌面端以及 390×844 移动端完成截图和可访问树检查；历史、账户、用户管理、下载分析均满足 `scrollWidth = clientWidth`，移动导航 Sheet 可正常打开并由 Escape 关闭。
- 下载分析页从 PostgreSQL 当前事实展示 43 条任务、15 个独立用户、14 个来源和完整日趋势；下载历史新账户空态、管理员列表数据态及权限拒绝态均有真实浏览器证据。
- 检查范围内浏览器页面错误与产品控制台错误为空；本机证据位于忽略目录 `dogfood-output/archive-qa/`。
- 当前 `main` 的 GitHub Actions 运行 `31765542909` 全部通过：Repository rules、Frontend quality、Backend quality、Runtime boundary 与 Required CI 均为 success，统一镜像与运行边界已验证。
- 首次 axe 矩阵在平台状态与平台目录复现 warning Badge 对比度 4.15:1 的 serious 违规；浅色 warning token 调整为 `#854d0e` 并重建统一镜像后，12 条公开/受保护路由在 1440×900 与 390×844 下 serious/critical 均为 0，深色 + reduced-motion 复扫同样通过。
- 本轮前端 lint/typecheck、183 文件格式检查、33 个测试文件/119 项测试和生产构建全部通过；仓库脚本测试增至 19 项并修复 Windows 下统一 CI 入口无法解析 `npm.cmd` 的历史问题。依赖锁定安装已在干净 Docker 构建中通过；本机另有运行中的 Next dev 进程锁定原生模块，故不以该 EPERM 作为产品失败。

final result: passed

## 2026-08-14 剧本文档列表与纯文本预览

- 新增受保护的 `/documents` 列表和 `/documents/detail?documentId=...` 详情；视觉采用现有 Vercel/Geist 无卡片内容流，列表用于定位提取任务，详情以可读的纯文本区作为主校验表面，并在桌面/移动导航增加“剧本文档”。
- `agent-browser` 在生产构建下覆盖 1280×900 与 390×844 的浅色/深色、长标题和长文件名、列表/详情/缺失 ID、刷新、跳过链接及移动 Sheet。所有页面满足 `scrollWidth = clientWidth`；Sheet 可由 Escape 关闭且焦点返回触发器，浏览器 console/error 为空。
- 预览中的 HTML-like 内容保持转义文本，DOM 不生成 `script` 节点；ready、verifying、failed、empty、请求失败、预览截断和质量警告均有自动化或浏览器证据。
- 巡检发现详情侧栏的 warning Alert 把图标、标题和正文作为三个网格项，390px 下标题被逐字挤压；现已将标题与正文组合为单一内容列，桌面与移动端均复验通过。证据位于忽略目录 `.codex-tmp/document-ui-qa/`。
- 工程门禁：production audit 0；lint/typecheck、format、37 个测试文件/133 项测试和 Next.js production build 通过。

final result: passed

## 2026-08-15 直接上传与 design.md 一致性回归

- source visual truth：`/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-2ab5eb65-a4a9-4200-a17e-19bb51b1436b.png`，1222×486 px，用户提供的本地视频入口裁切；同时以根 `design.md` 的“固定参数不做控件、辅助信息只在帮助任务时出现、Badge 只承载状态、正文/时长使用 Geist Sans”作为当前视觉判断基准。
- implementation evidence：`/Users/stephenqiu/.codex/visualizations/2026/08/14/01a00156-709b-7891-838c-39184921bf40/home-local-upload-after-1280x900.png`，1265×900 px；浏览器 CSS 视口 1280×900、DPR 2，截图输出已按 CSS 像素归一。移动证据为 `home-screenplay-direct-upload-390x844.png`，375×844 px；CSS 视口 390×844、DPR 2。
- state：已登录首页，本地视频 Tab 选中；移动补充状态为剧本文档 Tab 的空文件校验失败。参考图只覆盖入口局部，因此完整首页用于判断整体层级，入口局部用于同状态比较；没有把浏览器外壳或参考图缺失的 Hero 视为差异。
- full-view comparison：编辑式 H1、短说明、线型 Tabs、中性文件选择面和近黑主按钮继续使用项目既有无卡片语言。原确认行和底部说明移除后，主任务在首屏直接收敛为“选择文件 → 上传”，未出现新的边框、Card、阴影、胶囊或装饰图标。
- focused region comparison：参考图中的 P1 冗余权利勾选与长说明已移除；“上传并验证”改为面向用户任务的“上传视频”，文件说明由隔离存储实现细节收敛为“MP4 · 单个文件”。剧本文档入口同步采用“上传剧本”且无确认框，避免两个上传入口形成不同交互规则。
- comparison history：首轮发现确认控件阻断直接上传、技术实现文案占据次级层级；修复后 DOM 只保留文件选择、隐藏原生 file input 和主上传按钮。1280px 实测 `scrollWidth = clientWidth = 1265`；390×844 实测 `scrollWidth = clientWidth = 375`。移动 Sheet 打开后导航顺序为“首页 → 下载记录 → 剧本文档 → 平台状态”，滚动锁期间 `scrollWidth = clientWidth = 390`。
- interactions：本地视频与剧本文档 Tab 可切换；两种入口均不存在 checkbox；空文件提交返回对应可访问 Alert；移动 Sheet 可打开/关闭且保持稳定宽度。检查期间浏览器 console/error 列表为空。
- design.md 同步修复：规范化剧本预览从等宽字体恢复为 Geist Sans；媒体时长从 `font-mono` 改为 `tabular-nums`；分析完成状态 Badge 只显示“已完成”，执行次数回到相邻辅助文字。上述变更未修改颜色、圆角、网格、断点或主题 token，继续继承既有浅色/深色语义色。
- 工程门禁：lint/typecheck 通过；format check 221 个文件通过（仅既有损坏 symlink warning）；39 个测试文件、143 项测试通过；Next.js production build 与 15 个静态页面通过；Compose 统一镜像重建后 `/health/ready` 返回 200。

final result: passed

## 2026-08-15 下拉框视觉统一回归

- 验证目标：统一项目内所有基于共享 `Select` 组件的下拉框，使触发器、浮层、选中项和交互反馈符合 `design.md` 的克制、扁平、轻边界设计语言，同时保留 Radix Select 的可访问性与键盘行为。
- source visual truth：用户问题截图 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-4fba1066-b70e-404d-b1d0-d85e4e2a5c4b.png`；改动前同页面捕获 `/tmp/video-select-audit/01-current-select-open.png`。
- implementation evidence：桌面端 `/tmp/video-select-audit/02-revised-select-open.png`；390×844 移动端 `/tmp/video-select-audit/03-revised-select-mobile-open.png`；完整对照 `/tmp/video-select-audit/04-select-full-comparison.png`；重点区域对照 `/tmp/video-select-audit/05-select-focus-comparison.png`。
- state：桌面端改前与改后均为 1280×720、浅色主题、下载历史页“状态筛选”展开状态；移动端为 390×844 的相同展开状态。
- full-view comparison：浮层从贴合并覆盖触发器的卡片式展开，调整为触发器下方 4px 间距的稳定 Popper 布局；宽度严格跟随触发器，页面信息层级和对齐关系保持不变。缩放/滑入动画与偏重阴影被移除，改用轻边框、`shadow-sm` 和既有圆角 token。
- focused region comparison：选项最小高度统一为 36px，横向留白与勾选图标位置稳定；当前选中项使用轻量背景与中等字重，触发器打开态沿用现有 `accent` 语义，键盘焦点继续保留清晰 focus ring。
- mobile comparison：390px 视口下浮层保持在视觉中心列内，宽度与触发器一致，没有水平溢出或脱离布局中心；选项触控高度、文字间距和选中标记均保持可读。
- comparison history：初始浮层圆角、阴影、密度、对齐和展开动效与项目视觉语言不一致；统一修复仅修改共享 `frontend/src/components/ui/select.tsx`，所有消费者同步生效，没有页面级补丁或新依赖。
- interactions：鼠标点击可展开并选择；键盘 `Space`、`ArrowDown`、`Enter` 可完成展开、移动和选择，选择后触发器值正确更新。浏览器控制台无 error 或 warning。
- 工程门禁：lint/typecheck 通过；format check 通过；39 个测试文件、143 项测试通过；Next.js production build 与 15 个静态页面通过。
- 复核结果：桌面端、移动端和键盘交互均无剩余 P0、P1 或 P2 问题。

final result: passed

## 2026-08-17 下载详情页内容宽度回归

### 对照目标与实现

- 用户来源截图：`/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-b03822a8-eeb2-4059-9f57-7448c1862925.png`，用于确认下载详情页的内容区应与顶部导航、页面上下壳体共用同一水平宽度。
- 修复范围：已完成的《佳偶错成》第 1 集详情页；分析标题、操作区、视觉摘要和报告预览不再使用独立的 `max-w-4xl` 阅读宽度。
- 实现策略：继续复用现有 `.content-shell`，只移除详情内容内部的额外宽度约束；标题与操作按钮改为纵向分组，移动端保持自然换行。

### 浏览器实测

- 生产 Docker 前端重建后，1348×749 桌面视口中 Header、AI 分析区和底栏均为 `x=80 / width=1188 / right=1268`。
- AI 分析标题和视觉摘要均为 `x=80 / width=1188 / right=1268`，与共享内容轴完全重合。
- 390×844 移动视口中，分析区、标题和视觉摘要均为 `x=16 / width=358 / right=374`；`body.scrollWidth=390`、`document.scrollWidth=390`，无横向溢出。

### 工程验证

- 前端完整测试：145 项通过。
- `npm run lint`：通过；Biome 仅报告仓库既有 `.agents/skills` 断开符号链接 warning，TypeScript 通过。
- `git diff --check`：通过。
- Docker production build：通过；`video-api` 已重建并运行。

### Findings

- 没有发现新的 P0/P1/P2 视觉问题。
- 现有设计 token、字体、颜色、图片和图标均未改变。

final result: passed
