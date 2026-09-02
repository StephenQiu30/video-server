# 方案 3 无边框重设计 QA

## 2026-09-02 根路由会话启动态与 GSAP 过渡重构

- source visual truth：用户提供的刷新错误态 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-683960b4-9f69-4310-bc6b-7b5b1e2ff91f.png` 和最终登录工作区 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-b9e0b99f-d279-4e50-8572-1952c92605d5.png`。两张图确认刷新时完整公开首页先于登录工作区出现，问题覆盖 Header 与 main，而不是单个 Spinner 或局部淡入缺失。
- root cause：旧实现把完整 `PublicHome` 放进预渲染首屏 DOM，再依赖 hydration 后的 `invisible` 遮挡。服务器首屏无法仅凭客户端 HttpOnly 会话确定目标页面，样式或客户端脚本接管前仍可绘制错误内容；公开页到工作区的整页替换也没有连续的视觉状态。修复后直接读取开发服务器首屏 HTML并移除 script/style 内容，结果为 `hasStartup=true`、`hasPublicHome=false`、`hasWorkspace=false`、`hasHiddenPublicWrapper=false`，证明首屏不再携带可绘制的错误页面。
- transition design：首屏只显示与身份无关的 `FrameFetch / Session` 会话启动态、说明和 1px 进度线；认证完成后，启动态退出、正确内容分组进入，Header 操作同步淡入。`gsap.utils.selector/toArray` 将查询限制在组件作用域，`clamp/mapRange/distribute` 根据视口和节点数生成 8–14px 位移、160–200ms 时长与最多 100ms 错峰；没有渐变、阴影、Card 或新增视觉 token。
- authenticated refresh：真实 Chrome 登录会话在 `http://localhost:8102/` 冷刷新后的第一个可检查状态只有品牌、会话启动态和 Footer，不存在公开导航、公开首页或工作区；认证完成后 `data-home-phase=ready`、`data-home-view=workspace`、`publicViewPresent=false`、`workspaceViewPresent=true`、启动态已卸载。匿名浏览器同样先显示中性启动态，完成后只存在 `data-home-view=public`，工作区不存在。
- responsive and cleanup：Chrome 1280×800 与 390×844 均完成刷新回归，两个视口都满足 `scrollWidth=clientWidth`。桌面和移动的最终 `[data-motion-stage]` style 均为空，临时 `transform/opacity/will-change` 已清理；reduced motion 单元测试确认不创建 timeline 并立即完成交接。内容在过渡完成前使用 `inert` 与 `aria-hidden`，Header 只动画透明度/位移，不从辅助技术树隐藏真实导航。
- component composition：会话启动态复用 `Empty` 与支持 indeterminate 语义的 Radix `Progress`；公开首页的流程、能力和安全说明复用 `ItemGroup/Item` 组合。`MotionStage` 基于 Radix `Slot` 将首页与 Header 的动画阶段附着到已有组件或语义节点，不生成额外 DOM；`EditorialIntro` 与 `ItemTitle` 补齐可组合接口，页面只保留 `section/article/ol/li/h3` 等必要文档语义。
- engineering gates：完整 `npm run lint`、`npm run format:check`、58 个测试文件 / 234 项测试和 Next.js production build（20 个预渲染页面）全部通过。当前工作树另在 1280px 与 390px 真实浏览器中复核：页面有 5 个首页 `MotionStage`、3 个 `ItemGroup`、0 个旧动效标记，过渡完成后动效节点没有残留内联样式；两个视口均无错误覆盖或横向溢出。构建产物继续满足 `hasStartup=true`、`hasPublicHome=false`、`hasWorkspace=false`、`hasHiddenPublicWrapper=false`、`hasJsonLd=true`。

final result: passed

## 2026-09-01 全路由 BasicLayout 统一

- source visual truth：用户提供的欢迎页 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-2474a2bb-698e-49bd-8894-06a9eb528287.png` 与登录页 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-b3b43f17-5391-4389-baef-53deae0cac0a.png`，原始尺寸均为 2582×1740 px。来源要求不是只让两个页面视觉接近，而是让全部路由消费同一个 Header、main、Footer 与响应式 gutter 标准。
- implementation evidence：桌面欢迎页与登录页分别为 `/Users/stephenqiu/.codex/visualizations/2026/09/01/basic-layout-unification/home-desktop.png` 和 `/Users/stephenqiu/.codex/visualizations/2026/09/01/basic-layout-unification/login-desktop.png`；390×844 验证为 `/Users/stephenqiu/.codex/visualizations/2026/09/01/basic-layout-unification/home-mobile.png` 与 `/Users/stephenqiu/.codex/visualizations/2026/09/01/basic-layout-unification/login-mobile.png`。同输入比较图为 `/Users/stephenqiu/.codex/visualizations/2026/09/01/basic-layout-unification/source-vs-basic-layout.png`，上排是归一化来源、下排是统一布局后的实现。
- viewport and normalization：桌面浏览器使用 1291×749 CSS 视口；常驻滚动条后页面截图为 1276×740 px，`deviceScaleFactor = 1`。来源移除顶部 242px Chrome 外壳、右侧 30px 滚动条和底部 18px 非关键区域，将 2552×1480 内容区域按 2× 密度归一化为 1276×740，与实现逐像素等尺寸比较。移动浏览器使用 390×844 CSS 视口，常驻滚动条后截图为 375×812 px。
- state：未登录、浅色、页面顶部；补充验证登录页浅色→深色→浅色切换，主题切换前后 main 几何不变。登录页只显示认证上下文需要的主题动作，但 Header、操作槽、main 与 Footer 均来自同一个 `BasicLayout`。
- full-view comparison evidence：桌面欢迎页和登录页的品牌均为 `x = 80px / y = 18px / 77.3×44px`，Header shell 与 main 均为 `x = 80px / width = 1116px`；登录页主题按钮右边界与 shell 同为 1196px。移动两页品牌均为 `x = 16px / y = 18px`，Header/main 均为 `x = 16px / width = 343px`。每个页面实测只有一个 `[data-slot="basic-layout"]` 和一个 `main`，认证内容内部 `.content-shell` 数量为 0。
- focused region comparison：完整对照已经以等尺寸清晰展示品牌、主题入口、双栏标题、表单、Footer 和左右边界，无需再制造重复局部裁切。结构测试另外覆盖业务路由、公开根路由、认证恢复、管理员导航、移动 Sheet 和认证路由，确保统一不是只对截图中的两个页面生效。
- required fidelity surfaces：字体与标题继续使用 Geist/中文系统回退及现有 `.editorial-title`；所有根间距统一由 80px Header、`.content-shell` 和 80/32/16px gutter 管理；颜色只消费既有浅色/深色语义 token；品牌仍使用现有 `logo.svg`，图标仍使用 Phosphor；登录、注册、公开首页和业务导航文案未改写。没有新增 Card、边框、阴影、近似图标、装饰资产或平行主题。
- comparison history：第一轮存在 P1 架构分叉：业务页由 `BasicLayout` 渲染 Header/main/Footer，认证路由却由 `AppShell` 直接返回页面并在 `AuthPageFrame` 中重复 Header、main 和 `.content-shell`，因此任何单页校正都可能再次漂移。修复删除该旁路与 `AppShell`，在根 App Router layout 中无条件挂载唯一 `BasicLayout`，并把站内导航历史一起收回该布局；`AuthPageFrame` 只保留共享 main 内部的双栏内容。后验同输入比较与精确 DOM 测量没有剩余 P0/P1/P2。
- interactions and accessibility：跳过链接、唯一 main、唯一 H1、真实字段 label/button、Header 主题切换、移动响应式和 Footer 语义均保留；桌面与移动 `scrollWidth` 均等于可用页面宽度，没有横向溢出。浏览器控制台 error 为 0。
- engineering gates：BasicLayout 针对性 8 项测试、前端 lint/typecheck、格式检查、56 个测试文件共 221 项测试，以及 Next.js production build（20 个静态页面）全部通过。

final result: passed

## 2026-09-01 欢迎页与认证页网格统一

- source visual truth：用户提供的欢迎页 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-2474a2bb-698e-49bd-8894-06a9eb528287.png` 与登录页 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-b3b43f17-5391-4389-baef-53deae0cac0a.png`，均为 2582×1740 px。欢迎页提供目标导航网格与编辑式标题尺度；登录页记录修复前品牌、主题入口、双栏和标题落入另一套宽网格的问题。
- implementation evidence：桌面浅色欢迎页 `/Users/stephenqiu/.codex/visualizations/2026/09/01/welcome-auth-alignment/home-1440x1000.png`、桌面浅色登录页 `/Users/stephenqiu/.codex/visualizations/2026/09/01/welcome-auth-alignment/login-1440x1000.png`、桌面深色登录页 `/Users/stephenqiu/.codex/visualizations/2026/09/01/welcome-auth-alignment/login-dark-1440x1000.png`、390×844 欢迎页与登录页 `/Users/stephenqiu/.codex/visualizations/2026/09/01/welcome-auth-alignment/home-390x844.png` 和 `/Users/stephenqiu/.codex/visualizations/2026/09/01/welcome-auth-alignment/login-390x844.png`。移动并排证据为 `/Users/stephenqiu/.codex/visualizations/2026/09/01/welcome-auth-alignment/mobile-fixed.png`。
- viewport and normalization：桌面实现使用 1440×1000 CSS 视口、`deviceScaleFactor = 1`。来源图移除顶部 242px Chrome 外壳，将 2582×1498 页面区域等比缩放到 1440×836；实现截图裁为相同 1440×836。`/Users/stephenqiu/.codex/visualizations/2026/09/01/welcome-auth-alignment/source-vs-fixed.png` 的上排是来源欢迎页/登录页，下排是同视口修复后欢迎页/登录页，构成同一比较输入。
- state：未登录、浅色、页面顶部；补充验证登录页深色主题以及 390×844 响应式状态。来源包含浏览器外壳，比较前已按上述方式移除，不把浏览器 UI 当作产品差异。
- full-view comparison evidence：修复后两个页面的品牌链接均为 `x = 80px / y = 18px / 77.3×44px`，内容网格均为 `x = 80px / width = 1280px`，右边界均为 1360px；登录页主题按钮右边界同样为 1360px。欢迎页流程栏和登录表单的桌面起点均为 `x = 856.8px`，证明两页共享 `1.15fr / 0.85fr` 双栏与 96px 列间距。欢迎页 H1 和认证页产品主张计算字号均为 68px，统一消费 `.editorial-title`。
- focused region comparison：全视图对照中品牌、主题入口、两列起点、两组标题和 440px 表单均清晰可读，因此不再制作会重复相同证据的局部裁切。移动并排证据确认两页品牌均从 `x = 16px` 开始，欢迎页 main 与认证页 shell 都为 358px 宽；登录表单同为 `x = 16px / width = 358px`，页面 `scrollWidth = 390px`，没有横向溢出。
- required fidelity surfaces：字体与标题继续使用自托管 Geist、中文系统回退和现有 `.editorial-title`；间距由统一 `.content-shell`、80px Header、96px 桌面列间距和响应式 80/32/16px gutter 决定。浅色继续使用 `#FAFAFA/#0A0A0A`，深色画布实测为 `rgb(10, 10, 10)`，主题切换不改变几何。唯一可见品牌资产仍为现有 `logo.svg`，功能图标继续使用 Phosphor，没有生成、替换或近似绘制资产。登录、注册、产品主张和字段文案全部保留。
- comparison history：第一轮存在 P1 导航网格断裂：欢迎页使用桌面 80px gutter，而认证页使用 40px gutter，使 Logo、主题入口和内容边界整体错位；同时存在 P2 标题尺度与列起点漂移。实现移除第二套 `.page-shell`，认证页改为共享 `.content-shell`、欢迎页双栏公式和 `.editorial-title`。后验同输入及精确 DOM 测量没有剩余 P0/P1/P2；无新增 Card、边框、阴影或装饰性结构。
- interactions and accessibility：桌面与移动主题按钮均完成浅色↔深色切换，Header 与表单没有位移；认证页继续保持唯一 H1、真实 label/input/button、44px 品牌与主题触控高度。浏览器控制台 error 为 0，1440px 与 390px 均满足 `scrollWidth = viewport width`。
- engineering gates：针对性 AppShell 8 项测试、前端 lint/typecheck、格式检查、56 个测试文件共 221 项测试和 Next.js production build（20 个静态页面）全部通过。

final result: passed

## 2026-09-01 根路由认证恢复与 Header 宽度稳定性

- source visual truth：用户提供的刷新瞬间截图已保存为 `qa-output/018-header-auth-stability/source-refresh-chrome.png`（3372×1942 px，2× Chrome 窗口）。来源图明确显示公开首页内容已经出现，但 Header 暂时渲染了“首页 / 下载记录 / 剧本文档 / 平台状态”和灰色账户骨架，属于认证恢复状态泄漏而不是最终导航设计。
- comparison evidence：`qa-output/018-header-auth-stability/comparison-refresh-header.png` 将来源刷新态、修复后的中性认证等待态和认证完成后的公开导航纵向放在同一张 1280×540 输入中检查。修复后等待态只保留品牌与固定几何槽，不再显示错误导航、账户骨架或可误操作的主题/登录控件；完成态仍复用既有 shadcn/Radix 导航、按钮和主题组件。
- desktop geometry：1280×720 CSS 视口（常驻滚动条后页面截图 1265×712）中，认证等待、未登录完成和已登录完成三种状态的 `header-actions` 均为 `x = 579px / width = 606px / height = 44px`。公开导航位于同一个 458px 导航槽内并右对齐，登录按钮固定为 74×44px；已登录导航宽 458px，账户槽固定为 88×44px。三种状态的右边界均为 1185px，没有横向跳动。
- loading contract：根路由首个浏览器帧实测 `aria-busy="true"`、操作轨道宽 606px、主要导航不存在、Skeleton 不存在；认证完成后 `aria-busy` 移除并显示正确状态。直接读取开发服务器首屏 HTML 也只包含 `header-actions` 与 `header-auth-pending`，不包含 `header-account`、主要导航或 Skeleton，覆盖 SSR/hydration 前的真实刷新链路。
- mobile resilience：390×844 覆盖下（页面内容宽 375px），认证等待、公开完成和已登录完成三种状态的操作轨道均为 `x = 167px / width = 192px`，品牌右边界 93.3px，与操作轨道之间无重叠。公开态 GitHub、主题按钮均为 44×44px，登录为 74×44px；登录态主题与菜单均为 44×44px。`scrollWidth = bodyWidth = 375px`，没有横向溢出或小屏裁切。
- visual and accessibility review：Header 继续使用 80px 高度、`.content-shell`、Geist/中文系统回退、现有 `logo.svg`、Phosphor 图标和语义色；没有新增边框、阴影、卡片、近似图标或自定义绘图。中性等待态不暴露错误链接给键盘或辅助技术，固定轨道用 `aria-busy` 表达短暂状态；完成态的导航、主题、登录、账户和移动 Sheet 语义保持不变，所有可见 Header 控件仍满足 44px 触控高度。
- findings：来源中的 P1 认证恢复导航闪现和 P2 账户骨架/控件宽度跳动均已解决。桌面浅色公开态、桌面演示登录态、390px 公开态与 390px 登录态复核没有发现新的 P0/P1/P2；页面文案、标题层级、颜色、图片和主体布局均未改动。
- engineering gates：`npm run lint`、`npm run format:check`、56 个测试文件共 209 项测试、针对性 AppShell 测试和 Next.js production build（20 个静态页面）全部通过；随后已按要求重新以开发模式启动 8101 端口并完成冷刷新复验。

final result: passed

## 2026-08-31 公开首页连续画布与样式复用

- source visual truth：用户提供的公开首页截图已保存为 `qa-output/017-public-home-borderless/source-browser.png`（3372×1942 px，2× Chrome 窗口），并结合仓库 `docs/design/frontend-visual-system.md` 的匿名/已登录首页共享网格与无结构边界规则判断。
- implementation evidence：桌面浅色首屏 `qa-output/017-public-home-borderless/implementation-after-1686x850.png`（1671×842 px）、移动浅色首屏 `qa-output/017-public-home-borderless/implementation-after-390x844.png`（375×812 px）和移动深色首屏 `qa-output/017-public-home-borderless/implementation-after-dark-390x844.png`（375×812 px）。
- viewport and normalization：来源图移除顶部 242px 浏览器外壳与右侧 30px 滚动条后，由 3342×1684 按 2× 密度归一化为 1671×842；实现使用 1686×850 CSS 视口，常驻滚动条后 `clientWidth = scrollWidth = 1671`，浏览器页面截图为 1671×842。移动使用 390×844 CSS 视口，常驻滚动条后 `clientWidth = scrollWidth = 375`。
- state：未登录、浅色、页面位于 `/` 顶部；补充检查移动深色状态和桌面“产品能力”锚点激活状态。
- full-view comparison evidence：`qa-output/017-public-home-borderless/comparison-desktop.png`（3342×842）把来源与修复后实现横向放在同一输入中。实现保留 Header、品牌、公开导航、双栏首屏、流程、注册与源码入口，同时将独立营销页式超大标题和所有结构线收敛到应用既有连续画布。
- focused region comparison：全视图原始对照中的标题、按钮、流程文字与边界均可在 1:1 高度清晰判断；桌面后验图另保留原始 1671×842 像素，因此不需要重复裁切局部图。
- findings and required fidelity surfaces：字体继续使用自托管 Geist 与中文系统回退；匿名与已登录首页现在共同复用 `EditorialIntro` 和 `.editorial-title`，H1 从来源约 208px 高的独立 7.4rem 尺度收敛为约 65px 高的应用编辑式层级。Header、main、footer 继续共享 `.content-shell`；首屏与后续区段只通过 48/80/112px 网格和留白建立节奏。四个内容区计算边框的上、右、下、左均为 `0px`，能力列和双栏也没有 Separator、Card、阴影或独立背景。浅色继续使用 `#FAFAFA/#0A0A0A`，深色实测画布为 `rgb(10, 10, 10)`；按钮只消费已有 primary/secondary 表面。页面唯一图片资产继续复用现有 `logo.svg`，功能图标继续使用 Phosphor，没有新增近似资产。公开能力、自托管、安全边界、注册、源码和部署文案均保留，SEO 的唯一 H1 与顺序 H2/H3 结构未回退。
- accessibility and interactions：桌面导航“产品能力”点击后 URL 为 `/#capabilities`、目标顶部为 96px 且焦点保留在触发链接；主题按钮完成浅色→深色→浅色切换。注册、源码与部署说明链接保留真实地址；桌面与移动浏览器控制台均无 error/warning，820px 平板和 390px 移动端均没有越界元素。
- comparison history：第一轮来源存在两个可执行问题：P1 为匿名首页另建远大于应用首页的标题尺度和主张，形成明显产品风格断裂；P2 为首屏双栏竖线、区段横线和能力列分隔线违背当前“连续画布”规范。修复后匿名与已登录首页共享 `EditorialIntro`，统一“把素材，带回本地。”，并移除所有结构边界；同视口后验截图未发现新的 P0/P1/P2。无剩余 P3 视觉项。
- engineering gates：新增 2 项公开首页回归测试；`npm run lint`、`npm run format:check`、56 个测试文件共 209 项测试和 Next.js production build（20 个静态页面）全部通过。

final result: passed

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

## 2026-08-30 全路由无边框与信息密度回归

- source visual truth：用户提供的无边框管理员页面截图 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-1ebe3672-f6ed-4dbe-8da7-0bfdd399c757.png`，以及整改前同环境的 `/providers`、`/admin/providers` 与 `/admin/files` 截图。视觉判断继续服从根 `design.md` 和 `docs/design/frontend-visual-system.md`：无 Card 外壳、内容与留白分层、Radix/shadcn 官方组件、默认语义色和低信息密度。
- implementation evidence：同状态对照输入 `/Users/stephenqiu/.codex/visualizations/2026/08/30/all-pages-borderless-audit/comparison-before-after.png` 将平台状态和平台目录的整改前/最终 1920×971 截图并排放置。最终证据包含 `screenshots/52-final-providers-desktop.png`、`screenshots/43-after-admin-providers-desktop.png`、`screenshots/45-after-admin-files-desktop.png`、`46-after-admin-files-mobile.png`、`48-dark-home-mobile.png`、`49-dark-admin-files-mobile.png`、`50-dark-providers-desktop.png` 和 `51-dark-analytics-desktop.png`。
- route audit：`agent-browser` 覆盖首页、历史、剧本文档、平台状态、账户、文件管理、AI 服务、下载分析、平台目录、用户管理、两个缺失 ID 详情态、404、登录和注册共 15 个页面。1440×900 与 390×844 的全部页面均满足 `scrollWidth = viewport width`，浏览器页面错误为空。
- platform status：24 个平台由同权重长诊断列表改为“总数 / 当前可用 / 需关注”摘要、Radix Toggle Group 筛选、每页 8 项 Pagination 和默认收起的 Collapsible 验证详情；390px 页面高度由 7567px 降至 1815px。状态 Badge 继续使用项目默认语义 token，普通能力只使用辅助文字。
- provider catalog：使用 Field + InputGroup 搜索、Radix Select 公开状态筛选和每页 10 项 Pagination；桌面页面高度由 2580px 降至 1511px，390px 由 3812px 降至 2130px，保留 Table/Item 的无边框精确管理语义。
- persistent files：标准 Compose 下的列表错误根因为旧长标题超过响应模型 128 字符上限；上限与当前数据事实同步为 512 并补充集成测试。前端列表改用 ItemGroup/Item/Empty/Pagination，移除资产类型 Badge 与图标底座；超长标题在移动端截断但保留完整 `title`，修复前 `scrollWidth = 1441`，最终为 `390`。
- states and interaction：390px 移动 Sheet、桌面用户编辑 Dialog、平台诊断 Collapsible、目录搜索、Radix Select、分页、空态和错误态均完成真实交互检查。移动登录页重新捕获后与注册页均显示相同品牌入口，初始差异确认为截屏时序误报。
- themes and accessibility：浅色与深色覆盖首页、平台状态、下载分析和文件管理。axe WCAG 2 A/AA 在平台状态、文件管理、平台目录、下载分析和用户管理均为 0 violations；共享 Toggle Group 移除未选项低透明度后，浅色与深色均保持默认中性色和 AA 对比度。
- engineering gates：前端 `format:check`、lint/typecheck、47 个测试文件/184 项测试、Next.js production build 与 16 个静态页面、OpenAPI 漂移检查全部通过；后端 Ruff、Mypy 与 1228 项测试全部通过。完整 `docker compose up -d --build` 成功，前端、API、Media Runner 与出口代理健康，`/health/ready` 返回 200。Biome 只保留仓库既有 `.agents/skills` 断开符号链接 warning。
- findings：审查中的 2 个 High、1 个 Medium 已解决，1 个 Low 关闭为不可复现；没有剩余 P0/P1/P2 视觉或功能差异。完整记录位于 `/Users/stephenqiu/.codex/visualizations/2026/08/30/all-pages-borderless-audit/report.md`。

final result: passed

## 2026-08-29 下载详情页无边框信息层级重构

- source visual truth：用户来源截图 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-8c82fd38-7762-40f2-b104-e0cfc4b0fcb8.png`（3840×1942，Chrome 2× 截图）与根目录 `design.md`。来源状态是已完成任务，首屏包含播放器、右侧状态/元数据/取件操作和下方 AI 分析入口。
- implementation evidence：桌面浅色首屏 `/Users/stephenqiu/.codex/visualizations/2026/08/29/download-detail-borderless/desktop-light-viewport-1920x971.png`，桌面深色首屏 `/Users/stephenqiu/.codex/visualizations/2026/08/29/download-detail-borderless/desktop-dark-1920x971.png`，390×844 浅色首屏 `/Users/stephenqiu/.codex/visualizations/2026/08/29/download-detail-borderless/mobile-light-top-390x844.png`，390×844 深色首屏 `/Users/stephenqiu/.codex/visualizations/2026/08/29/download-detail-borderless/mobile-dark-top-390x844.png`。来源与实现已在同一比较输入 `/Users/stephenqiu/.codex/visualizations/2026/08/29/download-detail-borderless/source-vs-implementation.png` 中检查；左侧为来源页面，右侧为实现。
- viewport and normalization：来源图移除顶部 242px 的 2× Chrome 外壳后得到 3840×1700 页面区域，并缩放为 1920×850；实现使用 1920×851 CSS 视口捕获并补齐到同一 1920×850 单元。移动验收的浏览器外层为 390×844，页面 `clientWidth = scrollWidth = 375`；桌面常驻滚动条后 `clientWidth = scrollWidth = 1905`。
- information hierarchy：媒体标题与 `平台 · 来源 · 分辨率 · 编码 · 时长` 前置为唯一摘要，播放器与状态操作在桌面构成 1.55:0.65 双栏。来源页的垂直分隔线、播放器下重复标题、格式/分辨率/文件存储/执行尝试 `dl` 已移除；右栏只保留 Badge 状态、面向下一步的标题和说明、主操作与一个 Item 完整性摘要。AI 分析通过单一 Radix Separator 与首屏内容分章，不使用 Card、独立背景、阴影或装饰边框。
- official component use：媒体及失败态复用 AspectRatio，状态使用 Badge/Progress，主动作使用 Button，取消确认保留 AlertDialog，执行可信说明使用 Item；AI 配置使用 FieldGroup、Select、Textarea、Item 与 Button。原生标签只承担 `header`、`section`、标题、正文与媒体等必要语义，没有可点击 `div` 或页面级手写交互。
- responsive and themes：390px 下顺序实测为标题摘要 `→` 播放器 `→` 状态与操作，播放器顶部为 `356.1px`、状态区顶部为 `593.6px`，没有横向溢出。浅色画布为 `rgb(250, 250, 250)`，深色画布为 `rgb(10, 10, 10)`；深色前景为 `rgb(245, 245, 245)`，按钮、Badge、播放器和辅助文字继续消费既有语义 token，没有新增硬编码主题色。
- interactions and accessibility：页面保持唯一 H1、状态和 AI 分析两个顺序 H2，以及可读的播放器 region 和状态 region。Radix Select 实测可展开 listbox 并以 Escape 关闭；移动 Sheet 打开后焦点进入“导航”，Escape 关闭后 Trigger 回到 `data-state=closed`。桌面、移动与深色复验 console error 均为空。
- comparison history：来源基线存在一个 P2 信息层级问题：同一媒体标题和格式在播放器上下重复，且右栏用竖线与四项重复元数据形成类似卡片的独立面板。实现将标题提升到媒体/状态共同上方、删除重复元数据并以网格间距代替竖线；同输入复核后播放器、状态和操作形成连续读取路径，没有剩余 P0、P1 或 P2 视觉问题。
- engineering gates：`npm run lint` 通过，`npm run format:check` 通过，47 个测试文件、181 项测试全部通过；Biome 仅保留仓库既有 `.agents/skills` 断开符号链接 warning。Docker Compose 重新构建前端 production 镜像成功，Next.js 16 个静态页面生成通过，`video-frontend` 为 healthy，`/health/ready` 返回 200。

final result: passed

## 2026-08-29 下载分析图表主导式重设计

- source visual truth：用户指定的 shadcn/ui Area Charts 截图 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-50e54eef-cdc9-4fb1-b9a4-fd8deb194e17.png`（3840×1942，Chrome 2× 截图），以及同日读取的 [Area Charts](https://ui.shadcn.com/charts/area)、[Chart](https://ui.shadcn.com/docs/components/chart) 与 [Theming](https://ui.shadcn.com/docs/theming) 官方实现。官方交互面积图、Legend、Tooltip、`accessibilityLayer`、固定 `ChartContainer` 高度和 CSS 图表变量共同构成本轮设计事实。
- implementation evidence：蓝白桌面主视图 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-blue-white-1920x971.jpg`（1905×963）、桌面补充图表 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-blue-white-insights.jpg`（1905×963）、390×844 主视图 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-blue-white-390x844.jpg`（375×812）和移动端收起明细 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-blue-white-mobile-details.jpg`（375×812）均来自应用内浏览器真实渲染。
- viewport and normalization：桌面 CSS 视口 1920×971，浏览器常驻滚动条后 `clientWidth = scrollWidth = 1905`；移动 CSS 视口 390×844，`clientWidth = scrollWidth = 375`。来源图移除顶部 242px 的 2× Chrome 外壳后缩放至 1904×850，实现图裁为同尺寸并纵向合并；同输入全视图证据为 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-blue-white-comparison.jpg`（1904×1700）。
- state：30 天、浅色、892 条真实形态验收数据；桌面补充证据覆盖 KPI 与三列图表，移动补充证据为来源明细默认收起状态。来源图是组件目录而实现是业务分析页，因此比较聚焦主面积图比例、图例位置、三列图表节奏、蓝白层次、轻边界与信息密度，不把官网导航、示例文案和 Card 外壳当成业务差异。
- full-view comparison：实现将全宽双序列 AreaChart 提升为首个数据区，图例居中置于坐标轴下方，视觉比例和官方宽幅示例一致；项目既有 PageHeader、返回路径和周期 Toggle Group 继续占据业务所需标题层级。下方 KPI 与三列图表保持 Vercel/Geist 的无 Card 连续内容流，使用发丝分隔代替官网示例卡片墙。
- focused region comparison：补充图表证据确认状态环、完成率 AreaChart 和来源 BarChart 在一个连续三列网格内对齐；390px 下按任务状态、完成率、来源贡献顺序堆叠，坐标文字无裁切。来源精确表默认不挂载，通过官方 shadcn/ui Collapsible 的“查看 6 个来源”按需展开；桌面实测 `aria-expanded` 从 `false` 变为 `true` 且表格可见，移动默认 `aria-expanded=false` 且表格数量为 0。
- required fidelity surfaces：字体继续使用 Geist Sans 与中文系统回退；标题、轴标签和数字层级清晰，无错误换行。间距采用项目既有 content shell、6px 圆角和发丝分隔，无阴影、渐变、玻璃或卡片堆叠。图表只消费与 shadcn/ui Area Chart 官方示例一致的蓝色 `--chart-1` … `--chart-5` 序列；页面背景、按钮、筛选、进度和结构边界继续使用 Vercel 式黑白中性色，没有硬编码业务色。无位图、插画或伪造图形资产，全部可视化由官方 Chart 源码与 Recharts SVG 输出。文案只保留任务规模、完成质量、来源贡献和按需精确明细。
- accessibility and interactions：四个 ChartContainer 均提供独立可访问名称并启用 Recharts `accessibilityLayer`；主趋势与完成率保留屏幕阅读器精确数据表，来源贡献保留 meter，状态环提供四项图外数值。Collapsible 的桌面展开状态从 `false` 变为 `true` 且表格可见；移动默认 `aria-expanded=false` 且表格数量为 0；浏览器检查期间控制台没有 error。
- comparison history：第一轮主趋势仍位于 KPI 后方，1920×971 首屏只能看到图表上半部，属于 P2 视觉层级漂移；调整为“PageHeader → 主面积图 → KPI → 三列补充图表”后，主图完整进入首屏并与来源目标对齐。第二轮三列完成率图的 Y 轴被负 margin 裁切，属于 P2 可读性问题；移除负 margin、固定 40px Y 轴后，0/50/100% 均完整显示。用户随后要求降低 HTML/信息密度，本轮移除日均/峰值重复摘要与补充说明，并引入官方 Collapsible 收起完整来源表；最终桌面内容高度由约 2334px 收敛至约 2187px，未产生新的 P0/P1/P2 问题。
- engineering gates：新增官方 radix-nova Collapsible 源码并保持业务组件文件不超过 200 行；`npm run lint` 通过（仅既有 `.agents/skills` 断开符号链接 warning）；45 个测试文件、170 项测试全部通过；Next.js production build 与 16 个静态页面通过。全仓 `format:check` 仍只报告三个与本轮无关的既有文件：`admin-ai-providers/ai-provider-screen.tsx`、`analysis-result-view.tsx` 和 `lib/error-messages.ts`；本轮修改文件的 Biome 格式检查通过。

final result: passed

## 2026-08-29 下载分析信息层级与图表比例重构

- source visual truth：用户来源截图 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-ffac27f0-195d-4f35-aac6-1fc6148895dd.png`，原始 3840×1942 px；截图显示指标缺少清晰标题层级，趋势图随宽内容区等比放大并占据大部分首屏，来源洞察被推到首屏之外。
- implementation evidence：桌面同尺寸状态 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-redesign-1920x971.png`，1280×900 完整页面 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-redesign-1280x900.png`，移动端 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-redesign-390x844.png`。源图与 1920 桌面实现图已在同一视觉比较输入中检查；源图包含 Chrome 外壳且使用单条真实任务，实现图使用 30 天密集验收数据，因此对照聚焦页面信息层级、图表比例、控件几何和内容密度，不比较折线坐标本身。
- hierarchy：统计范围、周期和刷新收敛到 PageHeader 右侧；四项 KPI 进入有标题的连续概览区，通过横向发丝线和列分隔建立读取顺序。趋势与来源分布在桌面组成 2:1 双栏，来源前六项直接进入首屏，其余来源明确下沉到完整明细；没有新增 Card、阴影、渐变或侧栏后台壳。
- chart：桌面画布从 800×280 调整为 960×360，平板为 720×320，移动为 360×280；在 1920、1440、1280 和 390px 检查时均保持自然比例，原截图中的超高空图区域不再出现。系列图例可用按钮独立显隐，精确数值仍保留在语义化等价表格中。
- responsive and themes：390×844 下周期选择等分可用宽度，刷新保留 48px 触控区域，KPI 重排为两列，趋势、来源分布和 Item 明细依次单列；实测 `scrollWidth = clientWidth`。1280×900 深色模式首屏已检查，背景、前景、选中态、成功/失败线型和进度对比均继续消费既有语义 token。
- interactions and accessibility：PageHeader 保持唯一 H1；“周期概览”“下载趋势”“来源分布”“来源明细”使用顺序 H2；刷新按钮有明确可访问名称，根内容在后台刷新时暴露 `aria-busy`。Radix 周期单选和趋势多选的 checked/pressed 状态可读，趋势显隐交互完成浏览器复验，干净复验标签页的 console error/warning 为空。
- engineering gates：`npm run lint` 通过（仅仓库既有 `.agents/skills` 断开符号链接 warning）；44 个测试文件、168 项测试全部通过；Next.js 生产构建与 16 个静态页面生成通过；`/admin/analytics` 保持静态导出。
- findings：对照后没有剩余 P0、P1 或 P2 视觉差异；未改变颜色、字体、圆角、全局网格、接口契约或数据库结构。

final result: passed

## 2026-08-27 App 页面同步问题修复回归

- 修复首页解析结果与输入地址脱节的问题：URL 一旦变化即清除旧 inspection、发现结果、格式选择与创建任务入口；无效提交只保留可访问校验错误。
- 移动导航 Sheet 显式将打开后的初始焦点放到“导航”标题；390×844 实测活动元素为 `H2 / 导航 / tabindex=-1`，不再首先聚焦破坏性的退出操作。
- `/history` 的页面 metadata、H1、搜索控件、分页语义和辅助文案统一使用“下载记录”，与桌面导航、移动导航和 Flutter App 一致。
- 平台状态首次加载时的刷新按钮保留禁用语义，但不再用透明度降低文字对比度；加载文案明确为“刷新中…”。首页、下载记录和平台状态经 axe 4.12.1 复扫均为 0 violation。
- agent-browser 覆盖 1440×1000 与 390×844；移动页面 `body.scrollWidth = document.scrollWidth = innerWidth = 390`。修复证据位于 App 仓库 `qa-output/agent-browser-server-sync-20260827/screenshots/fix-*.png`。
- 工程门禁：lint/typecheck、format check、44 个测试文件共 167 项测试和 Next.js 生产构建全部通过。Biome 仅保留既有 `.agents/skills` 失效软链接 warning。

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

## 2026-08-29 shadcn/ui 官方图表组件与默认主题

- source visual truth：用户最新下载分析截图 `/var/folders/r5/lm_1_1hd321dzlfq0lctjdnw0000gn/T/codex-clipboard-5a68fde8-fe99-43b5-8144-7efe8ecedff8.png`、[shadcn/ui Area Charts](https://ui.shadcn.com/charts/area)、[Chart 文档](https://ui.shadcn.com/docs/components/chart) 与 [Theming 默认 neutral 主题](https://ui.shadcn.com/docs/theming)。官方文档明确以 `ChartContainer`、`ChartTooltipContent` 和 Recharts 组合图表，并推荐通过 `var(--chart-1)` … `var(--chart-5)` 使用默认主题色板。
- implementation evidence：浅色桌面截图 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-default-theme-1920x971.png`（1905×963）、390×844 移动截图 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-default-theme-390x844.png`（375×812）和 1280×900 深色截图 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-default-theme-dark-1280x900.png`（1265×889）均来自应用内浏览器真实渲染。浏览器预留 15px 常驻滚动条，三个视口均满足 `scrollWidth = clientWidth`，无页面级横向溢出。
- density normalization：来源图为 3840×1942、对应 1920×971 CSS 视口的 2× Chrome 截图；比较时移除顶部 360px 浏览器 chrome，将内容区降采样并与 Browser API 输出的 CSS 像素截图统一为 1904×784。全视图同输入证据为 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-default-theme-comparison.png`，图表/KPI 聚焦同输入证据为 `/Users/stephenqiu/.codex/visualizations/2026/08/28/01a0496c-b15e-7901-ad8c-177830e7aeb5/download-analytics-default-theme-chart-comparison.png`。
- component system：官方 `src/components/ui/chart.tsx` 源码保持不变；业务图表只通过 `ChartConfig`、`ChartContainer`、`ChartTooltipContent` 和 `var(--chart-*)` 组合趋势、状态环与来源条形图。普通页面与控件不消费图表色，周期 Toggle Group 和成功率 Progress 均恢复 shadcn/ui 的中性默认样式。
- required fidelity surfaces：Geist 字体、标题层级、内容轴、KPI 网格、间距、圆角、文案与原截图一致；无新增位图或装饰资产。浅色图表呈现官方默认橙/青/蓝色板，深色图表自动切换官方蓝/绿/黄/紫/红色板；来源和实现的周期选中态、成功率进度保持中性高对比。全视图已检查页面层级，聚焦图已检查 KPI、进度、图例与状态环颜色，无剩余 P0/P1/P2 差异。
- interactions and accessibility：趋势图例点击后“失败”系列切换为 `data-state="off"`，再次点击可恢复；三个 `ChartContainer` 均有独立可访问名称。趋势保留完整精确数据表，来源贡献保留 meter 与来源明细，状态环同时列出四项数值和百分比；浏览器控制台无 error。
- all-page color boundary：扫描 `src/app` 与除官方 `src/components/ui` 外的全部业务组件，未发现硬编码 Hex/RGB/HSL/OKLCH、Tailwind 一次性调色板类或将 `chart-*` 色扩散到普通控件；新增测试持续守住该边界。成功、警告、错误继续使用既有语义 token，避免丢失状态含义。
- comparison history：此前实现将用户选取的蓝色色板扩散到了周期选中态与成功率进度，属于 P2 视觉范围漂移。本轮改为官方 neutral 默认 `--chart-1` … `--chart-5`，并恢复两个普通控件的默认中性色；修复后的全视图和聚焦比较均未发现新的 P0/P1/P2 差异。
- engineering gates：目标文件 Biome 格式检查通过；`npm run lint` 通过（仅仓库既有 `.agents/skills` 断开符号链接 warning）；45 个测试文件、170 项测试全部通过；Next.js production build 与 16 个静态页面生成通过。全仓 `format:check` 仍只报告三个与本轮无关的既有文件：`admin-ai-providers/ai-provider-screen.tsx`、`analysis-result-view.tsx` 与 `lib/error-messages.ts`；本轮修改文件格式检查通过。

final result: passed

## 2026-08-30 严格无边框与 Radix UI 组件层回归

- source visual truth：用户本轮明确要求将“无边框”落实到页面内容层，并使用 @Vercel 规范下的 Radix UI 实现。整改前基线为 `/Users/stephenqiu/.codex/visualizations/2026/08/30/borderless-implementation-pass-2/screenshots/` 中 15 个 1440×900 当前运行态截图；同状态整改后截图位于相邻 `screenshots-after/`。
- component architecture：`frontend/components.json` 保持官方 `radix-nova` 源码风格，前端只依赖统一 `radix-ui` 包；Dialog、AlertDialog、Select、Tabs、RadioGroup、Progress、ToggleGroup、Collapsible、Sheet、DropdownMenu、Avatar 与 Slot 均由项目源码封装直接导入 Radix 原语。Radix 不提供的 Table、Button、Input 等继续使用项目内薄源码组件，没有新增平行 UI 库或业务页手写可点击 `div`。
- borderless implementation：共享 Table 移除表头线、页脚线和逐行边界；历史、文档、文件、Provider、用户、分析结果和剧本结果列表移除外沿与 ItemSeparator；账户、认证、解析结果和剧本文档工作区移除双栏竖线；下载详情、AI 结果、进度与元数据区移除页面 Separator。层级统一由 24/32/48px 间距、字重、字号、Radix 状态组件和必要的中性填充面表达。
- functional boundaries：保留键盘 focus ring、字段错误、Radix 弹层表面、Alert 语义、Radio/Switch 状态以及图表坐标网格；这些边界承担交互或数据读取，不作为页面装饰。业务页面 computed-style 扫描只命中 Button/InputGroup 的透明几何边界，没有剩余结构性可见边框。
- visual comparison：同视口对照 `/Users/stephenqiu/.codex/visualizations/2026/08/30/borderless-implementation-pass-2/comparison-before-left-after-right.png` 左侧为整改前、右侧为整改后，依次覆盖个人资料、下载分析和用户管理。整改后不再出现资料页十字线、图表/KPI 外沿、筛选区横线、表格外框或行线；蓝白 Area Chart 继续使用官方 `--chart-*` token。
- route audit：`agent-browser` 在 Docker 生产构建上覆盖首页、下载记录、剧本文档、平台状态、个人资料、文件管理、AI 服务、下载分析、平台目录、用户管理、两个缺失详情态、404、登录和注册共 15 个页面。全部 1440×900 截图已逐张检查；390×844 进一步覆盖首页、历史、账户、下载分析、用户管理和登录，均满足 `scrollWidth = innerWidth = 390`。
- themes and accessibility：下载分析桌面深色与用户管理移动深色均完成视觉复核；首页、历史、账户、下载分析和用户管理的 axe WCAG 2 A/AA 扫描均为 0 violations；全路由导航后的浏览器 page errors 为空。
- engineering gates：`npm run lint`、47 个测试文件/184 项测试、Next.js 16 个静态页面 production build、OpenAPI 漂移检查和格式检查通过；Biome 仅保留仓库既有 `.agents/skills` 断开符号链接 warning。`docker compose up -d --build` 成功，API、Frontend、Media Runner 与出口代理健康，`/health/ready` 返回 200。
- findings：整改前识别的页面分区线、表格线、列表分隔和双栏竖线已全部关闭；同输入视觉复核没有剩余 P0、P1 或 P2 无边框偏差。

final result: passed

## 2026-08-31 shadcn/ui Navigation Menu 与单击主题切换

- component architecture：通过 shadcn CLI 4.19.1 按项目既有 `radix-nova`、Radix base 和 neutral preset 安装官方 `navigation-menu` 源码。桌面主导航、移动 Sheet 内导航、页脚项目链接与剧本文档目录统一组合 `NavigationMenu`、`NavigationMenuList`、`NavigationMenuItem` 和 `NavigationMenuLink`；业务源码不再手写原生 `nav`，最终可访问语义由 Radix Primitive 输出。官方 shadcn `Pagination` 内部语义标签保持不变。
- boundary regression：`component-boundaries.test.ts` 将原生 `nav` 纳入业务组件禁用清单，同时继续允许 `src/components/ui/` 中可审计的官方源码。桌面、移动与目录测试均断言导航根节点的 `data-slot="navigation-menu"`，当前页仍保留 `aria-current="page"`，移动链接激活后仍由 Sheet 关闭。
- theme interaction：原 `ThemeMenu` 收敛为 `ThemeToggle`，使用 shadcn/ui `Button` 与 `next-themes`。主题集合固定为 `light`/`dark`、默认浅色、`enableSystem=false`，单次点击直接切换并持久化到 `framegrab-theme`；页面不渲染主题菜单、单选项或“跟随系统”。
- development runtime：停止 `video-frontend` 的 production standalone 容器后，使用 `next dev --hostname 127.0.0.1 --port 8101` 启动 Web；后端继续使用默认开发 Compose 的 `8111` 服务。本轮浏览器证据来自开发服务器，不使用 prod 运行态。
- browser evidence：agent-browser 在公开首页实测明→暗和暗→明均为一次点击；切换后 `html` class 与 `localStorage.framegrab-theme` 分别为 `dark`/`dark` 和 `light`/`light`，`role=menu` 与 `role=menuitemradio` 数量始终为 0。页面同时存在主要导航与页脚项目链接两个 `data-slot=navigation-menu` 根节点。390×844 视口为 `clientWidth=scrollWidth=390`，无横向溢出；axe WCAG 2 A/AA 为 0 violations、0 incomplete，浏览器页面错误为空。
- visual evidence：浅色桌面、深色桌面与 390px 浅色移动截图分别为 `/Users/stephenqiu/.codex/visualizations/2026/08/31/01a05720-dafb-7083-943f-d78cc54dde96/shadcn-navigation-theme/public-home-light.png`、`public-home-dark.png` 和 `public-home-mobile-light.png`。目视复核确认 80px Header、导航密度、主题按钮、Hero、内容轴与页脚没有 P0/P1/P2 视觉回归。
- engineering gates：`npm run format:check`、`npm run lint`、55 个测试文件/207 项测试和 Next.js 20 个静态页面 production build 全部通过；业务源码扫描只剩官方 `src/components/ui/pagination.tsx` 内的原生 `nav`。

final result: passed
