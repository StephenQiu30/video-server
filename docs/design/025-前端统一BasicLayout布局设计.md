# 前端统一 BasicLayout 布局设计

## 背景与问题

当前应用页由路由文件和业务 View 分别创建 `main`、`.content-shell` 与 `.inner-page`。同一类页面存在多套内容入口：首页、历史、详情、管理员页和 404 的主体容器并不由同一个布局边界管理；应用页没有全局 Footer；Header 虽然使用共享网格，但页面内容和 Header 的对齐责任分散在多个文件中。

这会带来三个可见问题：

- 页面主体左右边界与导航栏不一定处于同一条对齐线上。
- 短页面缺少稳定的底部结构，长短页面切换时整体节奏不一致。
- 页面状态、加载骨架和详情页各自替换 `main`，后续新增页面容易复制出新的宽度和留白规则。

## 设计目标

- Header、main 和 Footer 永远消费同一个 `.content-shell`，桌面最大宽度为 1376px。
- 应用页只有一个 `main`，由 `BasicLayout` 负责语义、宽度和纵向占位。
- Header 保持 80px，Footer 保持 64px 的稳定几何槽位，内容不足一屏时 Footer 贴近视口底部。
- 继续保留常驻纵向滚动容器和 Header 账户固定槽位，避免认证恢复、页面长短切换造成导航横向抖动。
- 页面业务组件只负责自己的内容结构和状态，不再创建页面级 `main` 或重复 `.content-shell`。

## 布局结构

```text
AppShell
└── BasicLayout
    ├── skip link
    ├── SiteHeader
    │   └── .content-shell / h-20
    ├── main#main-content
    │   └── .content-shell / flex-1
    │       └── page content
    └── SiteFooter
        └── .content-shell / h-16
```

`BasicLayout` 使用 `min-h-svh flex flex-col`。Header 和 Footer 都是不可收缩的常规流元素；main 使用 `flex-1` 填满中间空间。这里的“固定”指固定公共结构与几何尺寸，不使用 `position: fixed` 覆盖页面内容，也不使用固定 Footer 遮挡滚动区域。

## 网格与响应式约束

统一沿用全局事实来源 `src/app/globals.css`：

- 桌面：`width: min(calc(100% - 160px), 1376px)`。
- 641–1023px：两侧各 32px gutter。
- 不超过 640px：两侧各 16px gutter。
- Header、main、Footer 使用同一 `.content-shell`，不得在业务页面重新定义外层宽度。
- `.inner-page` 只负责常规内页的上下留白；首页 Hero 继续拥有自己的渐进顶部节奏。
- 认证页仍是唯一 `.page-shell` 双栏例外，不进入已认证应用的 BasicLayout。

## 页面迁移规则

所有已认证页面统一遵循以下规则：

1. `src/app/*/page.tsx` 只负责权限边界、Suspense 和页面级元数据。
2. 页面或业务 View 返回 `div`/`section` 内容，不返回 `main`。
3. 常规内页在内容根节点使用 `.inner-page`；首页只保留业务需要的底部留白。
4. 加载、错误、空态和详情缺失状态复用同一内容槽位，不重新创建 `.content-shell`。
5. 页面内部的表格分页 Footer 仍可使用语义化 `<footer>`，但它不是全局 SiteFooter，不承担页面外壳职责。

## 稳定性与可访问性

- `body` 保持 `overflow-y: scroll`，滚动锁定和宽度补偿继续交给 Radix 覆盖层原语。
- `main#main-content` 设置 `tabIndex={-1}`，Skip link 在键盘聚焦后可以直接落到唯一主内容区域。
- Header 账户区域继续保留固定宽度槽位，加载、未登录入口和 Avatar 菜单不会改变导航位置。
- Footer 只提供品牌返回入口和简短产品说明，不承载唯一必要信息或新增第二套导航。
- 认证页不显示应用 Header/Footer，避免登录/注册页面出现受保护应用导航语义。

## 验收标准

- 1280px、1536px 和 390px 视口中，Header/main/Footer 的左、右边界一致。
- 页面切换、滚动条出现/消失、认证恢复和账户菜单加载不会改变桌面导航的水平位置。
- 短页面 Footer 位于视口底部，长页面 Footer 在内容之后自然出现，内容不被遮挡。
- 页面 DOM 中应用页只有一个 `main` 和一个全局 `footer`；认证页保持现有无导航双栏结构。
- 所有现有路由、权限、返回路径、加载/错误/空态和移动 Sheet 行为不变。
