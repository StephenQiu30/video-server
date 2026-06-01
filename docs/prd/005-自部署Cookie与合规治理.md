---
layer: PRD
doc_no: "005"
audience:
  - PM
  - Dev
  - QA
  - Ops
feature_area: cookie-compliance
purpose: "定义自部署浏览器 Cookie 配置、合规提示、限流、配额和滥用治理边界。"
canonical_path: "docs/prd/005-自部署Cookie与合规治理.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/06-运维合规/02-风险与合规边界.md"
  - "docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md"
  - "docs/02-产品需求/03-MVP需求清单.md"
outputs:
  - "docs/plans/005-01-自部署浏览器Cookie配置计划.md"
  - "docs/plans/005-02-限流配额与合规负向计划.md"
triggers:
  - "需要支持自部署环境下的浏览器 Cookie 配置以解析需要登录态的视频"
  - "需要明确 Cookie 和合规治理的产品边界"
downstream:
  - "docs/acceptance/001-万能视频下载器MVP测试计划.md"
---

# PRD005 自部署 Cookie 与合规治理

## 1. 背景

当前万能视频下载器 MVP 阶段不托管用户平台 Cookie（见 `docs/06-运维合规/02-风险与合规边界.md`）。随着自部署场景的推进，部分平台公开视频解析需要浏览器 Cookie（如登录态、区域偏好等）才能正常获取视频信息。

同时，限流、配额和滥用治理是公网上线的必要门禁（见 `docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md`），需要在产品层面明确边界，避免系统被用于批量抓取、账号共享或其他违规用途。

本 PRD 定义两个子计划的产品边界：

1. **PRD005-01**：自部署浏览器 Cookie 配置
2. **PRD005-02**：限流、配额与合规负向

## 2. 目标

### 2.1 自部署 Cookie 配置

```gherkin
Given 自部署用户在本机环境运行 video-server
When 用户配置了目标平台的浏览器 Cookie 路径
Then Worker 能读取本机浏览器 Cookie 用于 yt-dlp 解析
And Cookie 仅在本机使用，不上传、不托管、不共享
```

```gherkin
Given SaaS 部署模式
When 任何请求试图上传或托管 Cookie
Then 系统明确拒绝并返回合规提示
```

### 2.2 限流配额与合规负向

```gherkin
Given 用户在 SaaS 环境使用下载服务
When 用户超过任务创建配额
Then 系统返回 429 限流响应，包含重试时间
```

```gherkin
Given 用户提交明显无效、保留域名、内网地址或非公开可访问链接
When 系统执行合规负向检查
Then 系统拒绝任务创建并返回明确错误码
```

## 3. 非目标

- 不提供 SaaS Cookie 上传、托管、共享或账号池。
- 不在 SaaS 环境读取服务端浏览器 Cookie。
- 不绕过平台登录、验证码、会员、付费、版权、地区、DRM、私密或删除状态。
- 不支持大规模批量抓取或自动化 Cookie 刷新。
- 不在本 PRD 中实现具体代码，代码实现在子计划中定义。
- 不改变已有 API 成功响应结构。

## 4. 核心内容

### 4.1 Cookie 配置产品边界

| 维度 | 自部署 | SaaS |
| --- | --- | --- |
| Cookie 来源 | 本机浏览器 Cookie 文件 | 不支持 |
| Cookie 上传 | 不需要（本机读取） | 拒绝 |
| Cookie 托管 | 不适用 | 不提供 |
| Cookie 共享 | 不适用 | 不提供 |
| Cookie 范围 | 仅 Worker 临时使用 | 不适用 |
| Cookie 持久化 | 不持久化到数据库或对象存储 | 不适用 |

Cookie 配置方式：

- 自部署用户通过环境变量 `YT_DLP_COOKIES_BROWSER` 指定浏览器类型（如 `chrome`、`firefox`、`edge`）。
- 或通过环境变量 `YT_DLP_COOKIES_FILE` 指定 Netscape 格式 Cookie 文件路径。
- Worker 在执行 yt-dlp 时使用 `--cookies-from-browser` 或 `--cookies` 参数。
- Cookie 仅在单次下载任务中临时使用，不写入日志、数据库或对象存储。

### 4.2 合规提示

自部署首次配置 Cookie 时，系统日志或配置检查应提示：

- Cookie 仅用于本机自部署环境。
- 用户应确保拥有相关平台账号的合法使用权。
- Cookie 中可能包含敏感凭证，不应与他人共享。
- 本系统不会上传、托管或持久化 Cookie。

### 4.3 限流与配额

| 接口 | 身份维度 | 默认策略 |
| --- | --- | --- |
| `/api/parse` | user id | 60 次 / 分钟 |
| `/api/tasks` (创建) | user id | 20 次 / 分钟 |
| 登录 | email hash + IP | 失败 5 次锁 15 分钟 |
| 注册 | IP | 10 次 / 小时 |

资源配额：

- 单任务最大文件大小：2GB。
- 单任务最大运行时长：2 小时。
- 全局下载并发数：2。
- 单用户下载并发数：1。
- 文件保留时间：24 小时。

### 4.4 合规负向检查

任务创建前必须拒绝：

- 明显无效 URL（非 HTTP/HTTPS 协议）。
- 保留域名（`localhost`、`127.0.0.1`、`0.0.0.0`、`*.local`、`*.internal`）。
- 内网地址（`10.*`、`172.16-31.*`、`192.168.*`）。
- 非公开可访问链接（需要登录才能访问且未配置 Cookie 的链接）。
- 已知 DRM 保护内容标识。
- 高风险平台或内容类型默认拒绝或要求人工确认。

### 4.5 滥用治理

- 公网部署必须启用鉴权和限流。
- 下载任务必须有并发、大小和时长限制。
- 对高风险平台和内容类型默认拒绝或要求人工确认。
- 产品文案不得宣传"下载任意受保护内容"。
- 日志脱敏：不得保存完整敏感链接，`token`、`signature`、`auth`、`cookie`、`key`、`access_token`、`session` 等参数必须脱敏。

## 5. 关联文档

### 5.1 输入文档

1. `docs/06-运维合规/02-风险与合规边界.md`
2. `docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md`
3. `docs/02-产品需求/03-MVP需求清单.md`

### 5.2 输出文档

1. `docs/plans/005-01-自部署浏览器Cookie配置计划.md`
2. `docs/plans/005-02-限流配额与合规负向计划.md`

### 5.3 下游文档

1. `docs/acceptance/001-万能视频下载器MVP测试计划.md`

## 6. 验收门禁

- 自部署 Cookie 配置仅在本机环境生效，SaaS 环境无 Cookie 上传/托管入口。
- 限流策略在 `/api/parse`、`/api/tasks`、登录、注册接口均有测试覆盖。
- 合规负向检查覆盖无效 URL、保留域名、内网地址等场景。
- Cookie 不写入日志、数据库或对象存储。
- 合规提示在配置检查或首次使用时展示。
- 所有验收标准在子计划中有对应的 TDD 测试和验证命令。

## 7. 风险与边界

- 自部署 Cookie 依赖用户本机浏览器，不同浏览器和操作系统的 Cookie 存储位置不同，需要 yt-dlp 的 `--cookies-from-browser` 能力支持。
- Cookie 中包含敏感凭证，日志脱敏必须覆盖 Cookie 相关字段。
- 限流 Redis 不可用时的 fail-open 策略会降低防滥用强度，但能避免 Redis 抖动导致核心业务不可用。
- 合规负向检查不能覆盖所有边界情况，需要持续迭代。

## 8. 待确认问题

- 自部署 Cookie 配置是否需要 Web UI 支持，还是仅通过环境变量配置。
- 限流 Redis fail-open 是否为生产默认策略。
- 合规负向检查的内网地址范围是否需要支持 IPv6。

## 9. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-01 | StephenQiu30 | 0.1.0 | 初始化 PRD：自部署 Cookie 配置、限流配额与合规负向治理边界 |
