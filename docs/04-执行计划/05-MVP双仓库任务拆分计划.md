---
layer: Plan
doc_no: "05"
audience:
  - PM
  - Dev
  - QA
  - Ops
feature_area: mvp-repository-split
purpose: "把 MVP 双仓库架构重构拆分为可执行、可测试、可 review 的 Epic 和任务。"
canonical_path: "docs/04-执行计划/05-MVP双仓库任务拆分计划.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/03-架构设计/04-MVP双仓库架构重构方案.md"
outputs:
  - "后端仓库 GitHub Issue 任务树"
  - "前端仓库 GitHub Issue 任务树"
  - "可执行任务优先级和依赖顺序"
triggers:
  - "开始执行 video-server 和 video-web 的 MVP 架构重构时"
downstream:
  - "docs/05-测试验收/06-MVP双仓库测试与Review门禁.md"
---

# MVP 双仓库任务拆分计划

## 1. 执行原则

1. 先文档和契约，再实现。
2. 先写失败测试，再写最小实现，再重构。
3. 每个 P0 任务必须有明确验收方式。
4. 每个主要阶段必须使用 `verification-before-completion` 做证据校验。
5. 每个主要功能完成后必须进入 code review，不带 Critical 或 Important 问题进入下一阶段。

## 2. 优先级定义

| 优先级 | 含义 |
| --- | --- |
| P0 | 首轮 MVP 必须完成，否则双仓拆分或主链路不成立 |
| P1 | 首轮建议完成，影响体验、维护性或验收质量 |
| P2 | 留边界或手工验证，本轮不阻塞主链路 |

## 3. 后端任务树

### E1 架构与契约

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| E1-T1 后端职责边界 | P0 | Architecture | 写明 API-only、Worker-only、对象存储、队列边界 | 架构文档不再把 SPA 托管列为长期职责 |
| E1-T2 OpenAPI 契约 | P0 | API Contract | 梳理 Auth、Parse、Tasks、Events、Download Link | 前端可仅凭契约开发 typed client |
| E1-T3 本地联调约定 | P0 | DevOps | 定义 CORS、端口、环境变量、启动顺序 | README 和 docs 中命令一致 |

### E2 后端纯化

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| E2-T1 隔离 SPA 静态托管 | P0 | Backend | 移除或开关化 FastAPI 静态文件兜底路由 | API 测试确认未知前端路由不由后端兜底 |
| E2-T2 认证 API 梳理 | P0 | Backend | 保留注册、登录、当前用户、JWT 依赖 | 未登录访问受保护 API 返回稳定 401 |
| E2-T3 任务 API 梳理 | P0 | Backend | 创建、列表、详情、取消、重试、事件、下载链接 | 用户不能访问他人任务和下载链接 |
| E2-T4 错误模型整理 | P0 | Backend | 统一 `code`、`message`、`details` | 前端能根据错误码展示状态 |

### E3 平台适配层

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| E3-T1 定义 `PlatformAdapter` | P0 | Backend | 匹配、清洗、解析、失败映射接口 | 单元测试可注入 fake adapter |
| E3-T2 建立 `AdapterRegistry` | P0 | Backend | 按 URL 或分享文案选择适配器 | 抖音/小红书/快手/西瓜/B 站识别测试通过 |
| E3-T3 yt-dlp 兜底适配器 | P0 | Backend | 保留当前格式提取和清晰度 preset | 现有 parse 测试不回退 |
| E3-T4 国内短视频最小适配 | P1 | Backend | 分享文案 URL 提取、平台识别、友好失败 | 不承诺复杂绕过和无水印能力 |
| E3-T5 合规边界测试 | P0 | Compliance | 禁止 Cookie 上传、DRM/付费墙承诺 | 文档和错误提示一致 |

### E4 后端测试与 CI

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| E4-T1 红灯测试：URL 清洗 | P0 | Test | 先写平台分享文案和 URL 归一化失败测试 | 测试先失败，后实现通过 |
| E4-T2 红灯测试：权限 | P0 | Test | 先写跨用户任务和下载链接越权测试 | 越权返回 403 或 404 |
| E4-T3 API 集成测试 | P0 | Test | parse、tasks、events、download-link | pytest 通过 |
| E4-T4 真实下载 smoke | P2 | Test | 手工脚本，CI 默认跳过 | 不影响主 CI 稳定性 |
| E4-T5 后端 CI | P0 | CI | pytest、lint 或项目既有检查 | GitHub Actions 独立通过 |

### E5 迁移收口

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| E5-T1 旧 `apps/web` 策略 | P0 | Migration | 新前端验收后删除或归档旧前端 | 不长期维护双前端 |
| E5-T2 README 后端化 | P0 | Docs | 改写为 API/Worker/基础设施说明 | 不再宣称同仓前端启动 |
| E5-T3 文档索引更新 | P0 | Docs | 索引新增本次 03/04/05 文档 | 阅读路径可追踪 |
| E5-T4 Superpowers review | P0 | Review | verification + code review | 有命令证据和 review 结论 |

## 4. 前端任务树

### F1 项目初始化

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| F1-T1 新建 `video-web` | P0 | Frontend/Repo | 使用 Build Web Apps 创建 Vite/React/TS 项目 | 独立 install、dev、build 可运行 |
| F1-T2 RadixUI 基础层 | P0 | Frontend/UI | Button、Input、Dialog、Tabs、Toast | 组件有基础测试和可复用样式 |
| F1-T3 路由骨架 | P0 | Frontend/App | `/`、`/auth`、`/workbench`、`/tasks/:id` | 路由测试通过 |
| F1-T4 数据层 | P0 | Frontend/Data | TanStack Query、API client、错误转换 | mock API 测试通过 |

### F2 标准文件和 docs

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| F2-T1 `AGENTS.md` | P0 | Docs/Repo | 迁移 TDD、SMART、docs、Git、交付规范 | 不包含后端专属命令 |
| F2-T2 `README.md` | P0 | Docs | 安装、启动、测试、构建、API 对接 | 新人可按 README 启动 |
| F2-T3 `.env.example` | P0 | DevEx | `VITE_API_BASE_URL` 等变量 | 本地联调配置明确 |
| F2-T4 前端 docs | P0 | Docs | 建立 03/04/05 文档 | 与后端文档互相引用 |

### F3 产品页面

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| F3-T1 落地页 | P1 | Frontend/UI | 现代 AI 工具风、平台能力、合规说明 | 移动端和桌面端无文本溢出 |
| F3-T2 登录注册 | P0 | Frontend/Auth | JWT、错误提示、跳转工作台 | 登录测试和 E2E 通过 |
| F3-T3 解析工作台 | P0 | Frontend/Core | 粘贴链接、解析、平台、格式选择 | 创建任务链路 E2E 通过 |
| F3-T4 任务列表 | P0 | Frontend/Core | queued/running/succeeded/failed 状态 | 状态组件测试通过 |
| F3-T5 任务详情 | P0 | Frontend/Core | 事件、重试、取消、下载入口 | agent-browser 能打开详情并断言关键状态 |
| F3-T6 错误空状态 | P1 | Frontend/UX | 未登录、解析失败、无任务、过期 | 用户可理解下一步动作 |

### F4 前端测试、E2E 和 Review

| Task | 优先级 | 类型 | 子任务 | 验收 |
| --- | --- | --- | --- | --- |
| F4-T1 红灯测试：登录态 | P0 | Test | 先写失败测试再实现 | Vitest 红绿证据记录 |
| F4-T2 红灯测试：解析表单 | P0 | Test | 输入、提交、错误展示 | Vitest 红绿证据记录 |
| F4-T3 红灯测试：任务状态 | P0 | Test | 状态映射和按钮可用性 | Vitest 红绿证据记录 |
| F4-T4 agent-browser 登录 E2E | P0 | E2E | mock API 登录到工作台 | 浏览器验证通过 |
| F4-T5 agent-browser 任务 E2E | P0 | E2E | 解析 mock、选格式、创建任务、详情 | 浏览器验证通过 |
| F4-T6 code review | P0 | Code Review | 主要功能完成后请求 review | Critical/Important 已处理 |

## 5. 跨仓依赖顺序

1. 后端 E1 和前端 F1/F2 可以并行。
2. 前端 F3 必须依赖后端 E1-T2 API 契约。
3. 后端 E2/E3 的红绿测试必须先于实现。
4. 前端 F4 的 agent-browser E2E 必须依赖 mock API，不依赖真实平台下载。
5. 旧 `apps/web` 的删除或归档必须等 `video-web` E2E 和后端 API 测试通过后执行。

## 6. GitHub Issue 对齐

| 仓库 | Issue | 覆盖范围 |
| --- | --- | --- |
| `StephenQiu30/video-server` | https://github.com/StephenQiu30/video-server/issues/1 | E1、E2、E3、E4、E5 |
| `StephenQiu30/video-web` | https://github.com/StephenQiu30/video-web/issues/1 | F1、F2、F3、F4 |

## 7. 子 Issue 映射

### 7.1 后端 `video-server`

| Issue | Task |
| --- | --- |
| https://github.com/StephenQiu30/video-server/issues/2 | E1-T1 定义后端职责边界 |
| https://github.com/StephenQiu30/video-server/issues/3 | E1-T2 定义 API 契约 |
| https://github.com/StephenQiu30/video-server/issues/4 | E1-T3 定义跨仓联调约定 |
| https://github.com/StephenQiu30/video-server/issues/5 | E2-T1 隔离 SPA 静态托管 |
| https://github.com/StephenQiu30/video-server/issues/6 | E2-T2 梳理认证 API |
| https://github.com/StephenQiu30/video-server/issues/7 | E2-T3 梳理任务 API |
| https://github.com/StephenQiu30/video-server/issues/8 | E2-T4 加固下载链接权限 |
| https://github.com/StephenQiu30/video-server/issues/9 | E2-T5 统一错误响应 |
| https://github.com/StephenQiu30/video-server/issues/10 | E3-T1 定义 PlatformAdapter |
| https://github.com/StephenQiu30/video-server/issues/11 | E3-T2 建立 AdapterRegistry |
| https://github.com/StephenQiu30/video-server/issues/12 | E3-T3 封装 yt-dlp 兜底适配器 |
| https://github.com/StephenQiu30/video-server/issues/13 | E3-T4 国内短视频分享文案最小适配 |
| https://github.com/StephenQiu30/video-server/issues/14 | E3-T5 B 站识别与失败映射 |
| https://github.com/StephenQiu30/video-server/issues/15 | E3-T6 合规边界 |
| https://github.com/StephenQiu30/video-server/issues/16 | E4-T1 URL 清洗红灯测试 |
| https://github.com/StephenQiu30/video-server/issues/17 | E4-T2 越权红灯测试 |
| https://github.com/StephenQiu30/video-server/issues/18 | E4-T3 API 集成测试 |
| https://github.com/StephenQiu30/video-server/issues/19 | E4-T4 真实下载 smoke 默认跳过 |
| https://github.com/StephenQiu30/video-server/issues/20 | E4-T5 后端 CI 独立通过 |
| https://github.com/StephenQiu30/video-server/issues/21 | E5-T1 旧 apps/web 策略 |
| https://github.com/StephenQiu30/video-server/issues/22 | E5-T2 README 后端化 |
| https://github.com/StephenQiu30/video-server/issues/23 | E5-T3 docs 索引和重构文档 |
| https://github.com/StephenQiu30/video-server/issues/24 | E5-T4 verification-before-completion 门禁 |
| https://github.com/StephenQiu30/video-server/issues/25 | E5-T5 requesting-code-review 门禁 |

### 7.2 前端 `video-web`

| Issue | Task |
| --- | --- |
| https://github.com/StephenQiu30/video-web/issues/2 | F1-T1 创建 video-web 独立项目 |
| https://github.com/StephenQiu30/video-web/issues/3 | F1-T2 RadixUI 基础组件层 |
| https://github.com/StephenQiu30/video-web/issues/4 | F1-T3 现代 AI 工具风样式系统 |
| https://github.com/StephenQiu30/video-web/issues/5 | F1-T4 React Router 路由骨架 |
| https://github.com/StephenQiu30/video-web/issues/6 | F1-T5 TanStack Query 和全局 Provider |
| https://github.com/StephenQiu30/video-web/issues/7 | F2-T1 前端 AGENTS.md |
| https://github.com/StephenQiu30/video-web/issues/8 | F2-T2 video-web README |
| https://github.com/StephenQiu30/video-web/issues/9 | F2-T3 .env.example 与 API base |
| https://github.com/StephenQiu30/video-web/issues/10 | F2-T4 前端 docs/03 架构设计 |
| https://github.com/StephenQiu30/video-web/issues/11 | F2-T5 前端 docs/04 执行计划 |
| https://github.com/StephenQiu30/video-web/issues/12 | F2-T6 前端 docs/05 测试验收 |
| https://github.com/StephenQiu30/video-web/issues/13 | F3-T1 现代 AI 工具风落地页 |
| https://github.com/StephenQiu30/video-web/issues/14 | F3-T2 登录注册和 JWT 登录态 |
| https://github.com/StephenQiu30/video-web/issues/15 | F3-T3 工作台解析流 |
| https://github.com/StephenQiu30/video-web/issues/16 | F3-T4 格式选择与创建任务 |
| https://github.com/StephenQiu30/video-web/issues/17 | F3-T5 任务列表与实时状态 |
| https://github.com/StephenQiu30/video-web/issues/18 | F3-T6 任务详情页 |
| https://github.com/StephenQiu30/video-web/issues/19 | F3-T7 全局错误和空状态 |
| https://github.com/StephenQiu30/video-web/issues/20 | F4-T1 登录态红灯测试 |
| https://github.com/StephenQiu30/video-web/issues/21 | F4-T2 解析表单红灯测试 |
| https://github.com/StephenQiu30/video-web/issues/22 | F4-T3 任务状态红灯测试 |
| https://github.com/StephenQiu30/video-web/issues/23 | F4-T4 agent-browser 登录 E2E |
| https://github.com/StephenQiu30/video-web/issues/24 | F4-T5 agent-browser 解析创建任务 E2E |
| https://github.com/StephenQiu30/video-web/issues/25 | F4-T6 agent-browser 任务详情 E2E |
| https://github.com/StephenQiu30/video-web/issues/26 | F4-T7 前端 CI |
| https://github.com/StephenQiu30/video-web/issues/27 | F4-T8 verification-before-completion 门禁 |
| https://github.com/StephenQiu30/video-web/issues/28 | F4-T9 requesting-code-review 门禁 |

## 8. 自审结论

本计划把 AI 总结、支付、会员、SEO/GEO 排除在 P0 外，避免首轮范围失控。平台专项适配的 P0 只承诺接口、识别、URL 清洗和失败原因，复杂平台能力按后续任务推进。测试与 review 作为门禁存在，不作为可选项。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-05-23 | StephenQiu30 | 0.1.0 | 初始化 MVP 双仓库任务拆分计划 |
