# Product Design QA

## 验收基准

- 主页视觉源：`/Users/stephenqiu/.codex/generated_images/019fd697-50b4-7891-9749-ed0f616f0ec6/exec-bf805af3-ea6b-4b24-91c1-1b5eda5b35cf.png`
- 任务页视觉源：`/Users/stephenqiu/.codex/generated_images/019fd697-50b4-7891-9749-ed0f616f0ec6/exec-e9ab43e4-7c29-4dfb-8865-992ee43a5b15.png`
- 实现截图：`reports/product-design-vercel-yupi-20260807/implementation-home-final.jpg`、`reports/product-design-vercel-yupi-20260807/implementation-task.jpg`
- 同屏对比：`reports/product-design-vercel-yupi-20260807/comparison-home.png`、`reports/product-design-vercel-yupi-20260807/comparison-task.png`
- 视口：1440 × 1024 CSS px；设备像素比：2；截图输出：1425 × 1024 px（扣除浏览器滚动条）
- 主页状态：Bilibili 公开链接解析成功，真实封面可见，默认展示 4/8 个语义格式。
- 任务页状态：历史下载成功、分析尚未开始；历史 inspection 已过期，因此左栏展示既有回退封面与明确警告。

## 视觉与交互检查

- 已完全移除顶部步骤进度条；首屏直接进入居中解析入口和左右分栏工作区。
- 主页延续方案 3：左侧真实媒体信息，右侧格式表格和蓝色主操作；下方整合方案 2 的 AI 分析标签页预览。
- 任务详情页延续方案 2：28/72 媒体侧栏与 AI 分析工作区，采用 1px 中性边框、白色背景与 Ant Design 蓝色主题。
- 未虚构接口不存在的作者、发布日期、文件大小、字幕、登录或支付能力。
- 实测真实封面 `src` 为 `data:image/*`；格式展开后为 8 项；摘要、关键观点、行动项、思维导图标签均可切换。
- 任务页下载文件、返回新建下载、分析模板、输出语言与开始分析入口均保持真实交互。
- 页面无横向溢出、重叠、裁切或异常圆角；桌面视口首屏完整覆盖核心下载路径。
- 新建浏览器标签复核主页与任务页，控制台无运行时错误；仅有开发服务器 HMR 和 React DevTools 提示。

## 迭代记录

1. 将居中单列结果卡改为媒体/格式双栏，移除黑色按钮并统一为 `#1677ff`。
2. 将格式单选列表改为真实字段驱动的表格行，并补充移动端两列标签布局。
3. 将 AI 分析能力整合为主页可切换预览，并把任务页收束为连续的分析工作区。
4. 生产构建后重启开发服务器，清除旧资源索引造成的历史控制台错误，再以新标签复验。

final result: passed
