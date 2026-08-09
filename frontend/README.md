# 帧取 · 万能视频下载器前端

基于 [Ant Design Pro](https://pro.ant.design) 官方脚手架（Umi Max v4 + antd v6 + ProComponents v3）构建的万能视频下载器前端。

## 技术栈

- **构建**：[Umi Max](https://umijs.org/docs/max/introduce) v4（`@umijs/max`）
- **UI 组件**：[Ant Design](https://ant.design) v6 + [ProComponents](https://procomponents.ant.design) v3
- **主题色**：`#1677FF`（Ant 主色），品牌 logo 位于 `public/logo.svg`
- **路由**：`config/routes.ts`
- **请求**：`@/utils/request` 基于 axios，处理 RFC Problem Details 错误；`src/services/` 下类型化 API 客户端由 OpenAPI 生成
- **部署**：UMI 静态产物 `dist/` 由后端 FastAPI 同源托管（`backend/app/web/spa.py`）

## 环境要求

- Node.js ≥ 22
- npm（使用 `package-lock.json`）

## 开始使用

```bash
npm install
npm run dev        # 本地开发，代理 /api 到 http://127.0.0.1:8101
npm run build      # 生产构建，产物输出到 dist/
npm run lint       # Biome + tsc 检查
npm test           # Vitest 单元测试
```

## 目录结构

```
config/            # Umi 配置（路由、主题、代理、布局设置）
public/            # 静态资源（logo、favicon）
src/
├── app.tsx        # 运行时布局配置
├── pages/         # 业务页面（路由组件）
│   ├── Download/        # 解析与下载主页
│   ├── DownloadDetail/  # 下载任务详情 + AI 分析
│   ├── History/         # 下载历史
│   ├── Account/         # 当前用户资料
│   ├── AdminUsers/      # 管理员用户管理
│   └── User/            # 邮箱登录与注册
├── components/    # 跨页业务组件（MediaCover、AnalysisPanel 等）
├── hooks/         # 下载与分析业务 hooks
├── services/      # API 客户端（video/ 目录由 OpenAPI 生成）
├── utils/         # request、格式化、校验、幂等键
└── types/         # 业务类型别名
tests/             # Vitest 单元测试
```

## 重新生成服务客户端

后端运行时，执行：

```bash
npm run openapi
```

使用 Ant Design Pro 内置的 `max openapi`（`@umijs/max-plugin-openapi`），根据 `config/config.ts` 的 `openAPI` 配置重新生成 `src/services/video/`。

## 与后端联调

开发时 `config/proxy.ts` 已将 `/api`、`/health`、`/docs`、`/redoc` 代理到 `http://127.0.0.1:8101`。
生产环境由后端 FastAPI 托管 `dist/` 静态产物，无需代理。

## 技术要点

- 页面路由按路由 `name` 使用 `menu.*` 国际化文案（`src/locales/zh-CN.ts`、`en-US.ts`）。
- `getInitialState` 通过 `/api/auth/me` 恢复用户；请求遇到 401 时统一轮换 Refresh JWT 并重试一次，JWT 不进入 localStorage。
- Umi Max `access` 根据当前用户角色控制管理员路由；后端仍独立执行角色校验。
- `exportStatic` 为每个路由生成 HTML，配合后端 SPA 回退到 `index.html`，支持浏览器路由刷新。
