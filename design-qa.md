# 方案 2 设计 QA

## 对照目标与证据

- 视觉真值：`/Users/stephenqiu/.codex/generated_images/019fe595-9cfd-7e10-8cc2-ca36f82e7f0b/exec-093b654f-524e-4641-aeb6-a196aa75c23c.png`
- 最终实现截图：`/Users/stephenqiu/Desktop/StephenQiu/Video/video-server/design-qa-implementation-desktop-final.jpg`
- 最终全景对照（左为方案 2，右为实现）：`/Users/stephenqiu/Desktop/StephenQiu/Video/video-server/design-qa-comparison-desktop-final.jpg`
- 聚焦对照：`design-qa-comparison-focus-hero-final.jpg` 与 `design-qa-comparison-focus-workspace-final.jpg`
- 移动端证据：`design-qa-implementation-mobile-final.jpg` 与 `design-qa-implementation-mobile-lower-final.jpg`
- 路由与状态：`/?design=inspection`，开发态设计检查用户，Bilibili 链接已解析，1080P 已选中。

## 视口与密度归一化

- 源图像素：1487×1058；按 1487×1058 CSS 目标视口解读。
- 桌面实现 CSS 视口：1487×1058，`devicePixelRatio = 2`。浏览器截图已归一化为 1487×1058 像素，即 1 个截图像素对应 1 个 CSS 像素，与源图等尺寸比较。
- 全景对照图：2974×1058，左右均为 1487×1058，无缩放或额外画布留白。
- 移动端 CSS 视口：390×844。由于系统滚动条和浏览器截图边界，证据图为 375×812；DOM 实测 `scrollWidth = clientWidth = 375`，无页面级横向溢出。该证据仅用于响应式检查，不与桌面源图做像素级判断。

## Findings

最终对照无可操作的 P0、P1 或 P2 差异。

- 字体与排版：Geist/PingFang 组合的字重、字号、字距和标题光学层级与源图一致；桌面媒体标题已收敛为单行，窄屏按内容自然换行。
- 间距与布局节奏：Header、Hero、72px 链接框、步骤条、双栏工作区与页脚的纵向基线已对齐；实现与源图均为约 1180px 主内容宽度。
- 颜色与 token：白色表面、冷灰文字/分隔线与 Apple 蓝主操作符合方案 2；浏览器计算样式确认主色为 `rgb(0, 122, 255)`（`#007AFF`），焦点和选中态使用同一语义 token。
- 图像质量：使用 1672×941 的 16:9 项目内生成封面，虚构电竞选手、右侧人物与左侧对局的主体关系和裁切方向与源图一致，无拉伸、透明光晕或占位图。
- 文案与内容：主标题、副标题、三步流程、下载文案与合规提示与方案 2 一致。文件大小和发布日期未伪造：当前 OpenAPI 格式契约不提供这两个字段，实现改用契约中的媒体 ID 与时长。
- 图标：全部可见图标来自 Phosphor 同一图标族，线宽、大小和对齐一致；未使用 emoji、CSS 绘图或手写 SVG 替代资产。
- 交互与可访问性：链接清空/重填、Radix 格式单选、键盘方向键选择、账户菜单打开/Escape 关闭均已浏览器实测。控件有语义标签和可见焦点，动画尊重 reduced motion。
- 响应式：390px 下链接框切换为垂直表单，双栏收敛为格式列表后接媒体预览；主操作、标题、合规提示与封面均未被裁切。

## 对照历史

1. Pass 1 证据：`design-qa-comparison-desktop-pass1.jpg`
   - P2：链接框仅 64px，Hero 与步骤条相对源图偏下；演示状态显示 8 个格式和额外的行尾选中图标；媒体标题换成两行。
   - 修复：链接框调整为 72px，重置 Hero/步骤/工作区间距；演示格式收敛为方案 2 的 4 档，移除重复选中图标，将标题字号调整到单行容量。
   - 复核：`design-qa-comparison-desktop-pass2.jpg`，上述差异已消除。
2. Pass 2 证据：`design-qa-comparison-desktop-pass2.jpg`
   - P2：主内容已匹配，但页脚比方案 2 高约 40px；移动页脚间距调整后桌面 `scrollHeight` 一度为 1071px，超过 1058px 目标视口。
   - 修复：增加页脚前节奏，同时将主区底部 padding 从 32px 收敛到 16px，保留页脚基线且消除桌面滚动条。
   - 复核：`design-qa-comparison-desktop-final.jpg`，DOM 实测 `scrollWidth = 1487`、`scrollHeight = 1058`，与目标视口一致。

## Open Questions

- 无阻塞问题。封面中人物为隐私安全的虚构电竞选手，不复制源图可识别人物；这是明确的资产约束，不影响布局和产品信息层级。

## Implementation Checklist

- [x] 1487×1058 等尺寸全景对照。
- [x] Hero 与解析工作区聚焦对照。
- [x] 方案 2 信息层级、白色表面和 Apple 蓝色 token。
- [x] 390×844 首屏与下半流程检查，无横向溢出。
- [x] 核心鼠标/键盘交互和账户菜单检查。
- [x] 浏览器日志检查：无 warning/error，仅 React DevTools 与 HMR 信息。

## Follow-up Polish

- P3：若未来 OpenAPI 格式模型增加预估文件大小或发布日期，可按方案 2 在格式行和媒体元数据中补充；当前不伪造后端未提供的数据。

final result: passed
