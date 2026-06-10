# Tasks: STE-265 平台画像注册与识别

## T1: TDD Red — 编写 X 和 Instagram 识别测试

**Files:** `apps/api/tests/test_platform_profiles.py`

- [ ] 编写 `test_platform_profile_matches_x_hosts` 测试
- [ ] 编写 `test_platform_profile_matches_instagram_hosts` 测试
- [ ] 更新 `test_all_platforms_have_profile_fields` 添加 X 和 Instagram 用例
- [ ] 更新 `test_high_risk_platforms_have_compliance_note` 添加 X 和 Instagram 用例
- [ ] 运行测试确认红灯

## T2: 实现 — 添加 X 和 Instagram 平台画像

**Files:** `apps/api/app/services/platforms.py`

- [ ] 添加 X 平台画像（x.com, twitter.com, social-platform）
- [ ] 添加 Instagram 平台画像（instagram.com, social-platform）

## T3: 分类对齐 — 将分类改为 PRD02 定义

**Files:** `apps/api/app/services/platforms.py`, `apps/api/tests/test_platform_profiles.py`

- [ ] 将 `domestic_short_video` 改为 `cn-short-video`
- [ ] 将 `long_video` 改为 `cn-video`（bilibili）或 `overseas-video`（youtube, vimeo, dailymotion）
- [ ] 将 `short_video` 改为 `overseas-short-video`（tiktok）
- [ ] 更新测试中的分类断言

## T4: 更新 SOURCE_SITE_NAMES

**Files:** `apps/api/app/services/download_adapter.py`

- [ ] 添加 `"x": "X"` 到 SOURCE_SITE_NAMES
- [ ] 添加 `"instagram": "Instagram"` 到 SOURCE_SITE_NAMES

## T5: 全量验证

- [ ] 运行 `npm test` 确认全部通过
- [ ] 更新 PRD02 状态为 implemented
- [ ] 更新 PLAN03 状态为 implemented

## T6: 提交

- [ ] `test:` 提交红灯测试
- [ ] `impl:` 提交实现
- [ ] `docs:` 提交文档更新
