---
layer: Acceptance
doc_no: "06"
audience:
  - Dev
  - QA
  - Ops
feature_area: mvp-repository-split
purpose: "定义 MVP 双仓库重构的红绿测试、agent-browser E2E、验证和 code review 门禁。"
canonical_path: "docs/05-测试验收/06-MVP双仓库测试与Review门禁.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/03-架构设计/04-MVP双仓库架构重构方案.md"
  - "docs/04-执行计划/05-MVP双仓库任务拆分计划.md"
outputs:
  - "后端测试门禁"
  - "前端测试门禁"
  - "agent-browser E2E 门禁"
  - "Superpowers review 门禁"
triggers:
  - "提交、合并、声明完成或进入下一阶段前"
downstream:
  - "GitHub Issue 验收清单"
---

# MVP 双仓库测试与 Review 门禁

## 1. 总原则

1. 任何核心逻辑变更必须先写失败测试，再实现最小代码，再重构。
2. 任何完成声明必须先运行对应验证命令，并读取输出。
3. 任何主要功能完成后必须进行 code review，Critical 和 Important 问题未处理前不得进入下一阶段。
4. agent-browser E2E 默认验证 mock 链路，真实平台下载 smoke 默认不进入 CI。

## 2. 后端测试门禁

| 场景 | 测试类型 | 必须覆盖 | 通过标准 |
| --- | --- | --- | --- |
| URL 清洗 | pytest unit | 分享文案、无 scheme URL、非法 URL | 解析前 URL 标准化稳定 |
| 平台适配选择 | pytest unit | 抖音、小红书、快手、西瓜、B 站、yt-dlp 兜底 | registry 选择符合预期 |
| 解析 API | pytest API | 成功解析、平台失败、非法 URL | 响应有稳定错误码 |
| 任务 API | pytest API | 创建、列表、详情、取消、重试 | 状态转换正确 |
| 权限 | pytest API | 跨用户任务、下载链接越权 | 返回 403 或 404，不泄露对象链接 |
| 对象存储 | pytest unit/integration | 下载链接、过期、缺失对象 | 过期或缺失有清晰错误 |
| Worker | pytest unit | 下载成功、失败、取消、事件记录 | 事件和状态一致 |

后端真实平台下载 smoke 只做手工或定时验证，必须用显式环境变量开启，CI 默认跳过。

## 3. 前端测试门禁

| 场景 | 测试类型 | 必须覆盖 | 通过标准 |
| --- | --- | --- | --- |
| 登录态 | Vitest + Testing Library | token 存取、未登录跳转、登录错误 | 组件状态和路由正确 |
| API client | Vitest | 401、403、422、409、410、5xx | 错误模型映射稳定 |
| 解析表单 | Vitest + Testing Library | 输入、清空、提交、loading、失败 | 用户状态可见 |
| 格式选择 | Vitest + Testing Library | 推荐格式、不可用格式、创建任务 | 按钮状态正确 |
| 任务列表 | Vitest + Testing Library | queued/running/succeeded/failed | 标签、按钮、进度正确 |
| 任务详情 | Vitest + Testing Library | 事件流、重试、取消、下载入口 | 权限和状态文案正确 |

前端测试不得依赖真实视频平台，必须通过 mock API 或测试 fixture 保持稳定。

## 4. agent-browser E2E 门禁

agent-browser 覆盖以下稳定链路：

1. 打开落地页，进入登录页。
2. 使用 mock API 登录成功。
3. 跳转工作台。
4. 粘贴 mock 视频分享文案。
5. 解析返回平台、标题、封面和格式。
6. 选择格式并创建任务。
7. 打开任务详情。
8. 验证事件、状态、下载入口或失败原因。

E2E 不验证真实平台可用性，不把网络平台波动作为 CI 成败依据。

## 5. Superpowers 门禁

### 5.1 verification-before-completion

每次声明完成前必须回答：

| 问题 | 要求 |
| --- | --- |
| 哪个命令证明完成？ | 写出完整命令 |
| 命令是否刚刚运行？ | 必须是当前轮新鲜结果 |
| 输出是否确认通过？ | 必须读取 exit code 和失败数量 |
| 是否有未验证内容？ | 必须明确说明 |

### 5.2 requesting-code-review

以下节点必须 code review：

1. 后端 API-only 改造完成。
2. 平台适配层 P0 完成。
3. 前端项目骨架和标准文件完成。
4. 前端工作台主链路完成。
5. agent-browser E2E 接入完成。
6. 删除或归档旧 `apps/web` 前。

Review 结论处理规则：

| 严重程度 | 处理规则 |
| --- | --- |
| Critical | 必须立即修复，不得继续 |
| Important | 进入下一阶段前必须修复或给出证据反驳 |
| Minor | 可记录为后续任务，不阻塞主链路 |

## 6. CI 门禁

| 仓库 | 必须命令 | 说明 |
| --- | --- | --- |
| `video-server` | `pytest` 或项目既有后端测试命令 | 覆盖 API、权限、平台适配、Worker |
| `video-server` | OpenAPI/配置检查 | 确保前端契约稳定 |
| `video-web` | `npm run typecheck` | TypeScript 类型检查 |
| `video-web` | `npm run test` | Vitest 单元和组件测试 |
| `video-web` | agent-browser E2E 命令 | mock 浏览器主链路 |

实际命令以各仓库 README 和 package scripts 为准；如果某命令尚未创建，执行任务必须先补齐脚本，再将该脚本写入 README。

## 7. 验收矩阵

| 验收项 | 后端 | 前端 | E2E | Review |
| --- | --- | --- | --- | --- |
| 双仓边界 | API-only 测试 | API base 配置 | 联调通过 | 架构 review |
| 登录和权限 | JWT/越权测试 | 登录态测试 | 登录链路 | 安全 review |
| 解析创建任务 | parse/tasks 测试 | 表单/格式测试 | 创建任务链路 | 业务 review |
| 任务详情 | events/download-link 测试 | 详情组件测试 | 详情链路 | UX review |
| 平台适配 | registry 测试 | 平台展示测试 | mock 平台链路 | 合规 review |

## 8. 自审清单

- [ ] 是否每个 P0 任务都有测试或明确验证方式。
- [ ] 是否所有完成声明都要求新鲜命令证据。
- [ ] 是否把 agent-browser 作为前端 E2E 工具，而不是 Playwright。
- [ ] 是否避免真实平台波动影响 CI。
- [ ] 是否明确 code review 的触发节点和处理规则。
- [ ] 是否避免把 AI 总结、支付、会员、SEO/GEO 放入首轮验收。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-05-23 | StephenQiu30 | 0.1.0 | 初始化 MVP 双仓库测试与 Review 门禁 |
