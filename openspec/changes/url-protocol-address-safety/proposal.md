## Why

PRD01 要求系统在 URL 进入下载链路前完成协议校验与地址安全检查。生产代码 `apps/api/app/utils/url.py` 中的 `normalize_user_url()` 已实现全部规则，但缺少 API 层集成测试证据来验证 `/api/tasks` 和 `/api/parse` 端点确实在入口处拒绝危险 URL。本次变更补充测试覆盖并建立 OpenSpec 规范基线。

## What Changes

- 新增 API 层集成测试文件 `test_url_safety_integration.py`，验证 `/api/tasks` 和 `/api/parse` 端点对 localhost、内网 IP、回环、保留地址、非法协议、空 URL 等场景返回 422
- 补充 `test_url_normalization.py` 中 multicast IP、`*.invalid` TLD、IPv6 私有/链路本地/组播地址的 unit test
- 创建 OpenSpec 规范 `url-protocol-address-safety`，记录 URL 安全的规范性要求
- 不修改生产代码（`normalize_user_url()` 已满足 PRD01 全部接收规则）

## Capabilities

### New Capabilities

- `url-protocol-address-safety`: URL 协议校验与地址安全规则的规范性要求，覆盖 http/https 协议限制、有效主机名验证、localhost/内网/保留/组播地址拒绝、空/非法输入处理

### Modified Capabilities

（无现有 spec 需修改）

## Impact

- 新增测试文件：`apps/api/tests/test_url_safety_integration.py`、`apps/api/tests/test_url_normalization.py` 补充
- 不涉及生产代码变更、API 变更或依赖变更
- 测试通过 `npm test` 验证
