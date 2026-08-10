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

## 工程门槛

- `npm run lint`：通过。
- `npm run format:check`：仓库存量 CRLF 换行基线仍会报告 129 项差异；本次 6 个变更的前端文件已通过定向 Biome check。
- `npm test`：25 个测试文件、83 项测试全部通过。
- `npm run build`：Next.js 16.3 静态导出通过，9 个业务路由与 404 均成功生成。
- 独立前端差异审查：无剩余 P0/P1；报告的 P2 已全部修复。

final result: passed
