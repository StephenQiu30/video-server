# FrameFetch 界面设计规范

本文件是 FrameFetch Web 界面唯一的视觉设计标准。2026-09-24 起，产品采用黑白中性色主题和 shadcn/ui 官方组件样式。用户确认的这一方向取代此前的彩色渐变、胶囊按钮、额外阴影和手工改写组件源码的方案。历史版本保留在 Git 记录中。

## 基础技术与来源

- Web 使用 Next.js、Tailwind CSS v4、shadcn/ui 的 `radix-nova` 样式与 Radix primitives。以 `frontend/components.json` 的 `style`、`base`、图标库配置为准。
- 按项目配置使用 shadcn CLI 添加或更新组件。组件源码与样式保持对应官方 registry 的默认实现；仅为修复明确的可访问性或功能缺陷修改组件源码，并记录原因。
- 组合页面时优先使用已有的 Button、Badge、Card、Dialog、DropdownMenu、Field、Input、InputGroup、NavigationMenu、Select、Table、Tabs、Textarea、Tooltip 等组件。交互状态使用组件自带的 `variant`、`size` 和 Radix 状态属性。
- 页面级 `className` 只负责布局：宽度、网格、排列、间距与响应式位置。不要用它改写组件的颜色、字号、圆角、阴影、高度、内边距或边框。

## 色彩与字体

- 页面基底为白，文字为近黑；层次由 shadcn neutral 的 `background`、`foreground`、`card`、`muted`、`border` 等语义 token 表达。
- 深色模式为上述中性色的反转。主题只配置在 `frontend/src/app/globals.css` 的 light/dark token 中，不在业务组件里写一套手工 `dark:` 色彩覆盖。
- Logo 保留原有品牌色，不加黑白滤镜；页面基底和主要操作使用黑白/灰阶。不要使用彩色 mesh、彩色渐变、彩色装饰背景、霓虹光晕或彩色链接作为页面主视觉。
- 图表使用不同明度的灰阶，并配合文字、图例或形状区分数据。错误状态可沿用 shadcn 官方 `destructive` 语义；状态不能只靠颜色传达。
- 正文和标题使用项目现有的 Geist 与中文系统回退字体。页面标题按内容层级排版，避免把普通页面标题做成营销海报字。

## 布局与密度

- 同一页面的标题、表单、结果、列表和页脚共用内容容器左边界。响应式收窄时保持相同的阅读顺序。
- 留白应服务信息分组。不要用大面积空白、放大的 hero、高度固定的空区域或背景装饰补足页面。
- 页面与章节可使用简单容器、网格和 `gap-*`。不增加为单一页面定义的复杂视觉 CSS。
- 原生 shadcn 组件默认尺寸优先；相邻控件通过相同的 `size` 选择对齐，避免局部 `h-*`、`px-*` 让按钮和输入框变形。

## 组件与交互

- Button 使用官方 `variant` 与 `size`；不要改成自定义胶囊、阴影或品牌色。
- Tabs 使用官方 `Tabs`、`TabsList`、`TabsTrigger`、`TabsContent` 与内置 variant。保持 Radix 的键盘导航、焦点和选中态。
- Table 使用官方 `Table` 组合及默认单元格间距和垂直对齐。列头与单元格保持相同列宽和文字对齐；数值列可右对齐，长文本可按列需求换行或截断。不要为各表复制一套不同的单元格 padding。
- Toast 使用 shadcn 的 Sonner 包装和 `sonner` 的 `toast()`；短暂任务通知使用 toast，必须持续展示的状态放在页面内容中，危险确认使用 AlertDialog。
- 表单优先使用 Field、Input、InputGroup、Select 等现有组合，保留标签、错误说明、禁用状态和键盘焦点。
- 对话框、菜单、导航与提示使用 Radix/shadcn 原生语义和焦点管理。所有图标按钮须有可读名称。

## 验收

- 每次视觉变更先核对官方 CLI/文档与 `components.json`，预览组件差异。
- 在亮色与暗色、桌面与窄屏检查真实渲染；验证 Tabs 切换、表单提交、Toast、Table 对齐、键盘焦点与响应式布局。
- 提交前运行项目已有的格式、类型和相关测试。视觉改动以浏览器渲染为最终依据。
