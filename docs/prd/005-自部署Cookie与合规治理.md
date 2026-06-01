---
layer: PRD
doc_no: "005"
audience:
  - PM
  - Dev
  - QA
  - Ops
feature_area: trust-compliance
purpose: "定义自部署 Cookie 治理和合规负向场景的产品边界与验收标准。"
canonical_path: "docs/prd/005-自部署Cookie与合规治理.md"
status: done
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/02-产品需求/04-上线级SaaS需求清单.md"
outputs:
  - "docs/plans/005-02-限流配额与合规负向计划.md"
triggers:
  - "需要验证合规边界和安全防护"
downstream:
  - "Feature PR"
  - "验收测试"
---

# 自部署 Cookie 与合规治理

## 1. 背景

系统作为公开视频下载工具，需要在合规边界内运行。用户只能下载自己拥有版权、已获授权、公共领域或平台明确允许保存的内容。系统必须防止未授权访问、资源滥用和敏感信息泄露。

## 2. 目标

### 2.1 认证与授权

```gherkin
Given 用户未登录
When 用户尝试创建解析或下载任务
Then 系统返回 401 未授权错误
And 不创建任何任务
```

### 2.2 配额限制

```gherkin
Given 用户已登录
When 用户的日常任务额度已用完
Then 系统返回 429 错误，错误码为 limit_exceeded
And 错误消息说明额度已用完
```

```gherkin
Given 用户已登录
When 用户的存储额度已用完
Then 系统返回 429 错误，错误码为 limit_exceeded
And 错误消息说明存储额度已用完
```

```gherkin
Given 用户已登录
When 用户的并发任务数已达到限制
Then 系统返回 429 错误，错误码为 limit_exceeded
And 错误消息说明并发限制
```

### 2.3 限流

```gherkin
Given 用户已登录
When 用户在短时间内发送大量请求
Then 系统返回 429 错误，错误码为 rate_limited
And 错误消息说明请求过于频繁
```

### 2.4 敏感信息保护

```gherkin
Given 系统处理请求时发生错误
When 系统返回错误响应
Then 响应中不包含 cookie、token、secret 或 password 等敏感参数
```

### 2.5 生产配置安全

```gherkin
Given 运维人员部署生产环境
When 使用 .env.production.example 作为配置模板
Then 模板中所有敏感值使用 CHANGE_ME 占位符
And 模板不包含 minioadmin 等默认凭证
And 模板不能直接用于生产环境
```

## 3. 非目标

- 不实现 DRM 绕过或付费墙绕过。
- 不实现会员内容绕过。
- 不实现私有内容绕过。
- 不在运行时代码中嵌入 Cookie 读取逻辑（仅 Worker 作业层允许浏览器 Cookie 例外）。

## 4. 合规边界

### 4.1 运行时禁止标记

以下标记不得出现在运行时代码中：

- `cookiefile`
- `drm_bypass`
- `paywall_bypass`
- `member_bypass`
- `private_bypass`

### 4.2 Cookie 边界

浏览器 Cookie 读取功能仅允许在以下文件中使用：

- `apps/worker/worker/jobs.py`（Cookie 读取器）
- `apps/api/app/core/config.py`（配置定义）
- `apps/worker/worker/jobs.py`（配置使用）

### 4.3 URL 重写

敏感查询参数（token、signature、auth、cookie、key、access_token、session）在日志和错误响应中必须被重写为 `***`。

## 5. 验收门禁

- 未登录用户不能创建解析或下载任务。
- 额度、并发、存储和大小限制返回明确错误。
- 敏感参数不进入日志或错误响应。
- 生产配置模板不能被误用为真实配置。
- 合规 smoke 脚本通过。

## 6. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-02 | StephenQiu30 | 0.1.0 | 初始化 PRD |
