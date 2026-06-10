---
layer: Spec
spec_no: "01"
audience:
  - Dev
  - QA
feature_area: platform-profiles
purpose: "定义平台画像数据结构、识别规则、合规要求和 API 契约。"
canonical_path: "openspec/specs/platform-profiles/spec.md"
status: accepted
version: "1.0.0"
owner: "StephenQiu30"
inputs:
  - "docs/prd/02-平台识别与平台画像.md"
triggers:
  - "新增或下线正式支持平台"
  - "调整平台画像字段或合规提示"
downstream:
  - "apps/api/app/services/platforms.py"
  - "apps/api/app/schemas.py"
---

# 平台画像规范

## 1. 概述

本规范固化首版正式支持的平台画像定义、平台识别规则、合规要求和 API 契约，作为实现层和验收层的唯一事实来源。

## 2. 正式支持平台

首版正式支持 5 个平台：

| platform_id | display_name | category | compliance_note |
| --- | --- | --- | --- |
| `youtube` | YouTube | overseas-video | 仅支持公开可访问内容，不承诺绕过登录、年龄验证或会员限制 |
| `bilibili` | Bilibili | cn-video | 仅支持公开可访问内容，不承诺绕过登录、大会员或区域限制 |
| `tiktok` | TikTok | overseas-short-video | 仅支持公开可访问内容，不承诺绕过登录或私密账号限制 |
| `x` | X | social-platform | 仅支持公开可访问内容，不承诺绕过登录或私密账号限制 |
| `instagram` | Instagram | social-platform | 仅支持公开可访问内容，不承诺绕过登录、私密账号或限时动态限制 |

## 3. 平台画像数据结构

每个平台画像 MUST 包含以下字段：

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `platform_id` | string | ✅ | 平台唯一标识，小写 ASCII |
| `display_name` | string | ✅ | 平台展示名称 |
| `category` | string | ✅ | 平台分类 |
| `compliance_note` | string | ✅ | 合规提示 |
| `hosts` | string[] | ✅ | 匹配的域名列表 |

### 3.1 平台分类

| category | 说明 | 示例平台 |
| --- | --- | --- |
| `overseas-video` | 海外长视频 | YouTube |
| `cn-video` | 国内长视频 | Bilibili |
| `overseas-short-video` | 海外短视频 | TikTok |
| `social-platform` | 社交平台 | X, Instagram |

### 3.2 合规要求

所有平台的 `compliance_note` MUST 遵守以下规则：

1. 不得承诺绕过登录限制
2. 不得承诺绕过验证码限制
3. 不得承诺绕过会员或付费限制
4. 不得承诺绕过私密访问限制
5. 不得承诺绕过区域或版权限制
6. MUST 明确声明"仅支持公开可访问内容"

## 4. 平台识别规则

### 4.1 域名匹配

1. 从 URL 中提取 hostname
2. hostname 归一化：小写、去除首尾点
3. 精确匹配或子域名匹配（如 `www.youtube.com` 匹配 `youtube.com`）

### 4.2 识别结果

| 场景 | 返回 |
| --- | --- |
| 匹配正式支持平台 | 返回对应 `PlatformProfile` |
| 匹配已知但非正式支持平台 | 返回 `None`（允许 yt-dlp best-effort） |
| 无法匹配任何平台 | 返回 `None` |
| 匹配被阻止的主机（localhost、内网等） | 抛出 `AppError` |

## 5. API 契约

### 5.1 ParseResponse 平台字段

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `platform_id` | string \| null | 平台唯一标识 |
| `platform_display_name` | string \| null | 平台展示名称 |
| `platform_category` | string \| null | 平台分类 |
| `compliance_note` | string \| null | 合规提示 |

### 5.2 TaskRead 平台字段

任务详情接口 SHALL 返回与 ParseResponse 一致的平台字段，确保前端可统一展示。

## 6. 产品边界

1. 平台识别成功 ≠ 下载一定成功
2. 对非正式支持平台，只允许 best-effort 提示，不做正式承诺
3. 产品文案不得表达规避平台限制或主动去水印能力

## 7. 验证场景

### 7.1 成功路径

- 提交 YouTube URL → 识别为 `youtube` 平台 → 返回完整平台画像
- 提交 Bilibili URL → 识别为 `bilibili` 平台 → 返回完整平台画像

### 7.2 失败路径

- 提交 localhost URL → 抛出 `AppError`
- 提交未知域名 URL → 返回 `None`（best-effort）

### 7.3 验证命令

```bash
npm test
```

## 8. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-06-10 | StephenQiu30 | 1.0.0 | 初始化平台画像规范 |
