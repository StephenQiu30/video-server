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

- 首屏结构与真值一致：导航与主体共用约 80px 内容边距、80px 无底边 Header、编号眉题、单行编辑式中文标题、68px 浅灰输入带、黑色主操作、媒体与设置双栏、发丝分隔和底部安全状态。
- 排版节奏一致：标题、描述、输入带和结果区的垂直起点与方案稿基本对齐；Geist、近黑文字、`#FAFAFA` 画布和小半径控件形成 Vercel Home 的克制层级。
- 无边框要求已落实：页面级 Card、筛选壳、认证壳和主要控件不使用可见描边或重阴影；只在表格行、内容分区、双栏和 Footer 保留必要的发丝线。
- 业务差异均为有意映射：最终实现展示 API 实际返回的 4 个完整格式，不复制稿中后端不存在的“字幕”“仅音频”“容器独立选择”和播放按钮；不虚构文件大小或精确 FPS。
- 生产数据缩略图缺失时显示明确的“封面不可用”状态；山景素材只用于 `?design=inspection` 演示，并已由 2.3 MiB PNG 压缩为约 221 KiB WebP。

## 响应式与交互验证

- 390×844 首屏自然收敛为标题、输入、主按钮、媒体和画质单列；下半屏的 4 个格式、真实元数据、创建任务与安全状态均可达。
- 移动 Sheet 可打开/关闭，包含视频解析、下载记录、个人资料、退出与主题切换；Sheet 无可见边框。
- 响应式导航在 820px 使用移动 Sheet、在 1024px 切换为桌面导航；Sheet 保留当前页 `aria-current="page"`、内部 `overflow-y: auto`、Escape 关闭与触发器焦点恢复。1024px 实测 Logo 为 32px、品牌文字为 17px，页面无横向溢出。
- Header 账户槽在认证恢复、未登录入口和 Avatar 菜单之间固定为 88px，已登录控件为 74×44px；共享 Button 与 `asChild` 导航链接的 computed `transform` 为 `none`，transition 仅包含 `background-color, color, opacity`，按下和异步状态不再改变组件几何。
- 浏览器实测：清空链接、重新填入链接、720P/480P/1080P Radio 切换、明暗主题切换、移动菜单、移动主题切换和主题跨刷新保持。
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

## 2026-08-12 下载分析 Radix 可视化回归

- 下载分析页继续使用无边框内容流：页面、筛选、指标、趋势和来源区均无 Card 外壳与装饰边框；仅指标列、数据表行保留必要发丝分隔，趋势绘图区使用无描边的中性实心表面。
- 7/30/90 天筛选改为单选 Radix Toggle Group；趋势图例使用多选 Radix Toggle Group，支持键盘逐项切换全部、成功、失败与取消系列；成功率和来源占比使用 Radix Progress，并保留等价精确数据表。
- 趋势图新增低对比总量面积层、末端数据点、日均任务与单日峰值摘要。桌面浅色、桌面深色和 390×844 移动端均完成真实渲染检查；系列开关高度为 44px，状态切换不改变布局几何。
- 桌面证据：`E:/StephenQiu/Video/qa-output/analytics-radix-desktop-final.png`；移动证据：`E:/StephenQiu/Video/qa-output/analytics-radix-mobile-final.png`；深色证据：`E:/StephenQiu/Video/qa-output/analytics-radix-dark.png`。
- 1440px 桌面与 390px 移动端均满足 `scrollWidth = clientWidth`；移动列表按 Item 摘要重排，未出现表格横向滚动。浏览器控制台仅包含开发态 React DevTools/HMR 信息，无产品代码错误。
- 当前工程门槛：lint/typecheck 通过；format check 172 个文件通过；31 个测试文件、108 项测试通过；Next.js 生产构建与 11 个静态页面导出通过。

final result: passed

## 2026-08-12 覆盖层滚动锁回归

- `agent-browser` 使用经典滚动条模式复现：根节点 `scrollbar-gutter: stable` 与 Radix 的 `react-remove-scroll` 同时补偿 15px，导致所有 Dropdown、Dialog、AlertDialog、Select 和 Sheet 触发器看起来像“按钮点击后整页抖动”。
- 根因修复以 `body` 的常驻纵向滚动条稳定长短页面切换，同时移除根节点的第二套滚动条槽位编排；未覆盖 `data-scroll-locked`，滚动锁、焦点圈定与 Escape 行为继续由 Radix 原语统一负责。
- 1440×500 下 Dropdown、Dialog、Select 打开前后 `.content-shell` 均为 `x = 80px / width = 1265px`；390×500 下移动 Sheet 打开前后均为 `x = 16px / width = 343px`。
- 浅色、深色和主题切换均无布局位移；浏览器页面错误为空。

final result: passed
