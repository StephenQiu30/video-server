---
layer: Design
doc_no: "04"
audience:
  - PM
  - Dev
  - QA
  - Ops
feature_area: mvp-repository-split
purpose: "定义万能视频下载器 MVP 从单仓混合形态迁移到后端 API 仓库 + 前端 React 仓库的架构边界。"
canonical_path: "docs/03-架构设计/04-MVP双仓库架构重构方案.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/02-产品需求/03-MVP需求清单.md"
  - "docs/03-架构设计/01-总体架构方案.md"
  - "docs/03-架构设计/02-技术选型候选.md"
outputs:
  - "video-server 纯后端边界"
  - "video-web 独立前端边界"
  - "跨仓 API 契约和测试责任划分"
triggers:
  - "执行 MVP 架构重构、前后端拆仓、前端新仓建设或后端 API-only 改造时"
downstream:
  - "docs/04-执行计划/05-MVP双仓库任务拆分计划.md"
  - "docs/05-测试验收/06-MVP双仓库测试与Review门禁.md"
---

# MVP 双仓库架构重构方案

## 1. 背景

当前项目已经具备 FastAPI、RQ、PostgreSQL、Redis、MinIO/S3、yt-dlp 和 Vite/React 前端雏形，但后端仍存在托管 SPA 静态文件的职责，前端也位于后端仓库内部。新的 MVP 目标是把项目拆成两个长期独立维护的仓库：

1. `StephenQiu30/video-server`：纯后端仓库。
2. `StephenQiu30/video-web`：完整独立前端仓库。

本方案只定义首轮 MVP 架构边界，不实现 AI 总结、支付、会员、SEO/GEO 等商业化扩展。

## 2. 目标

1. 后端收敛为 API-only + Worker-only：只负责 API、任务队列、下载执行、对象存储、鉴权、数据持久化和 OpenAPI 契约。
2. 前端使用 Build Web Apps 能力新建完整项目：React + TypeScript + Vite + RadixUI + TanStack Query + React Router。
3. 保留多用户账号体系：JWT、任务归属、任务权限和下载链接权限必须闭环。
4. 下载能力采用插件化适配：`yt-dlp` 通用兜底，国内短视频和 B 站等主流平台进入平台适配层。
5. 测试遵循红绿流程：先写失败测试，再实现，再重构；前端 E2E 使用 agent-browser。

## 3. 非目标

- 不在首轮实现 AI 视频总结、思维导图、问答、字幕导出。
- 不在首轮实现 Stripe、会员、额度、商业化支付。
- 不承诺全平台永久可用，不做 DRM、付费墙、会员内容绕过。
- 不接收、不上传、不存储用户 Cookie；本地浏览器登录态只允许作为自部署显式配置的后续能力。
- 不让后端继续长期托管前端静态产物。

## 4. 仓库边界

### 4.1 后端仓库 `video-server`

后端仓库保留以下职责：

| 模块 | 职责 |
| --- | --- |
| `apps/api` | FastAPI API、OpenAPI、鉴权、任务 API、解析 API、下载链接 API |
| `apps/worker` | RQ Worker、下载任务执行、对象上传、事件记录 |
| `packages/shared` | 任务状态、错误码、共享枚举 |
| `docs/03-架构设计` | 架构方案和决策 |
| `docs/04-执行计划` | 后端主导的跨仓执行计划 |
| `docs/05-测试验收` | 后端测试、跨仓联调和验收门禁 |
| `docker-compose.yml` | 后端运行和基础设施编排 |

后端仓库移除或隔离以下职责：

1. 构建前端产物。
2. 托管 SPA 静态文件。
3. 维护前端路由。
4. 在后端镜像中混入前端构建过程。

### 4.2 前端仓库 `video-web`

前端仓库承担以下职责：

| 模块 | 职责 |
| --- | --- |
| `src/app` | 路由、Provider、应用级状态 |
| `src/pages` | 落地页、登录页、工作台、任务详情页 |
| `src/features` | auth、parse、tasks、platforms 等业务切片 |
| `src/components` | RadixUI 组合组件和领域组件 |
| `src/lib` | typed API client、错误格式化、工具函数 |
| `e2e` | agent-browser E2E 脚本和说明 |
| `docs/03-架构设计` | 前端架构和 UI 设计边界 |
| `docs/04-执行计划` | 前端任务计划 |
| `docs/05-测试验收` | 前端单测、E2E 和评审门禁 |

`video-web` 必须从一开始就是独立项目，不从 `video-server/apps/web` 直接复制形成第二套旧结构。

## 5. API 契约

前端只通过后端公开 API 访问服务端。首轮契约包括：

| API 域 | 必要能力 |
| --- | --- |
| Auth | 注册、登录、当前用户、退出后的前端状态清理 |
| Parse | 输入 URL 或分享文案，返回平台、标题、封面、时长、格式列表 |
| Tasks | 创建任务、列表、详情、取消、重试 |
| Task Events | 查询任务事件或实时状态 |
| Download Link | 仅任务拥有者可获取下载链接 |
| Health | 本地联调和部署探活 |

错误响应需要稳定包含 `code`、`message` 和可选 `details`，前端不得依赖后端异常文本判断状态。

## 6. 平台适配层

平台适配层位于后端，目标是把平台识别、URL 清洗、能力声明和失败原因从 API Router 中剥离。建议接口：

| 单元 | 职责 |
| --- | --- |
| `PlatformAdapter` | 声明平台名、匹配规则、URL 预处理、解析策略 |
| `AdapterRegistry` | 按 URL 或分享文案选择适配器 |
| `YtDlpAdapter` | 通用兜底解析和格式提取 |
| `ShortVideoAdapter` | 国内短视频分享文案清洗和平台识别 |
| `BilibiliAdapter` | B 站链接识别和用户友好失败原因 |

首轮 P0 不要求每个平台都完成复杂无水印解析；P0 要求插件边界、平台识别、URL 清洗、yt-dlp 兜底和可测试失败原因成立。

## 7. 前端体验边界

前端采用“落地页 + 登录后工作台”：

1. 未登录用户看到现代 AI 工具风落地页，包含核心能力、支持平台、合规声明和登录入口。
2. 登录用户进入工作台，完成粘贴链接、解析、选择格式、创建任务。
3. 工作台展示任务列表、状态、失败原因、取消、重试、下载入口。
4. 任务详情展示事件流、下载状态、过期提示和权限错误。

UI 必须服务工具效率，不能用营销化页面替代核心工作台。

## 8. 合规与安全边界

1. 仅允许用户下载自己拥有版权或已获授权的内容。
2. 不提供 DRM、付费墙、会员内容绕过能力。
3. 不接收用户上传 Cookie，不把 Cookie 存入数据库、日志或对象存储。
4. 下载链接必须校验任务归属并设置过期时间。
5. 解析失败、平台不可用、登录态不足等情况必须返回用户可理解的错误。

## 9. Superpowers 工作流

本重构按 Superpowers 工作流执行：

1. `brainstorming`：确认范围、技术选择和拆仓边界。
2. `writing-plans`：把方案拆成可执行任务，并落入 docs 和 GitHub Issue。
3. `verification-before-completion`：每次声称完成前必须运行对应验证命令。
4. `requesting-code-review`：主要任务完成后进行 code review，Critical 和 Important 问题必须处理。
5. 后续实现可使用 `subagent-driven-development` 或 `executing-plans` 按任务推进。

## 10. 关联 Issue

| 仓库 | Issue |
| --- | --- |
| `StephenQiu30/video-server` | https://github.com/StephenQiu30/video-server/issues/1 |
| `StephenQiu30/video-web` | https://github.com/StephenQiu30/video-web/issues/1 |

## 11. 验收门禁

- 架构文档明确双仓边界，没有保留后端托管 SPA 的长期职责。
- 平台适配层有清晰接口和 MVP 非目标，不承诺不可控平台能力。
- API 契约覆盖登录、解析、任务、事件、下载链接和错误模型。
- 测试和 code review 门禁被写入执行计划与验收文档。

## 12. 风险与边界

| 风险 | 控制方式 |
| --- | --- |
| 专项平台适配范围失控 | P0 只做插件边界、URL 清洗、平台识别、友好失败 |
| 双仓联调复杂 | 使用 OpenAPI/typed client、`.env.example` 和 mock API |
| E2E 不稳定 | agent-browser 默认跑 mock 链路，真实下载 smoke 默认跳过 |
| 双前端并存 | `video-web` 通过验收后再删除或归档旧 `apps/web` |

## 13. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-05-23 | StephenQiu30 | 0.1.0 | 初始化 MVP 双仓库架构重构方案 |
