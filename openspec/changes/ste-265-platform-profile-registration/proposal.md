# Proposal: STE-265 平台画像注册与识别

## Summary

实现 PRD02 中定义的 5 个正式支持平台画像注册、平台识别和支持声明，确保 API 返回统一的平台字段和合规提示。

## Scope

- 新增 X 平台画像（x.com, twitter.com）
- 新增 Instagram 平台画像（instagram.com）
- 将平台分类对齐 PRD02 定义（cn-video, cn-short-video, overseas-video, overseas-short-video, social-platform）
- 更新 SOURCE_SITE_NAMES 包含 X 和 Instagram
- 更新测试覆盖所有 5 个 PRD 正式支持平台

## Non-goals

- 不新增 PRD02 未定义的平台
- 不修改下载适配器核心逻辑
- 不变更 API 接口签名

## Normative files changed

- `apps/api/app/services/platforms.py` — 平台画像注册表
- `apps/api/app/services/download_adapter.py` — SOURCE_SITE_NAMES 映射
- `apps/api/tests/test_platform_profiles.py` — 平台识别测试
- `docs/prd/02-平台识别与平台画像.md` — PRD 状态更新
- `docs/plans/03-平台画像注册与识别计划.md` — Plan 状态更新

## Validation

- `npm test` — 所有测试通过
- 5 个 PRD 正式支持平台均可被识别
- 每个平台有 display_name、category、compliance_note
