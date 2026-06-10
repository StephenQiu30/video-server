## Context

PRD01 定义了 URL 接收边界与安全校验规则。生产代码 `apps/api/app/utils/url.py` 中的 `normalize_user_url()` 已实现全部规则，包括：

- http/https 协议限制
- 有效主机名验证
- localhost/内网/回环/链路本地/组播/保留/未指定地址拒绝
- `*.localhost`/`*.local`/`*.invalid` TLD 域名拒绝
- 空字符串/非 URL 文本拒绝
- 分享文本自动提取 URL

单元测试 `test_url_normalization.py` 已覆盖 18 个场景。但缺少 API 层集成测试来验证 `/api/tasks` 和 `/api/parse` 端点在入口处的行为。

## Goals / Non-Goals

**Goals:**

- 补充 API 层集成测试，验证端点级别的 URL 安全拒绝行为
- 补充 unit test 缺口（multicast IP、`*.invalid` TLD、IPv6 私有/链路本地/组播）
- 建立 OpenSpec 规范基线

**Non-Goals:**

- 不修改生产代码（已满足 PRD01）
- 不做平台识别
- 不做任务队列/下载执行

## Decisions

1. **仅新增测试文件**：`normalize_user_url()` 已完整实现 PRD01 规则，无需修改生产代码。API 层通过调用该函数获得安全保障。

2. **测试结构**：`test_url_safety_integration.py` 使用 FastAPI TestClient 测试 `/api/tasks` 和 `/api/parse` 端点，结构与现有 `test_task_endpoints.py` 一致。

3. **不新增 OpenSpec spec 文件到 `openspec/specs/`**：URL 安全规则已通过 PRD01 和生产代码定义，本次变更仅补充测试证据，不引入新的长期规范要求。OpenSpec change 文档记录本次变更的决策和验收。

## Risks / Trade-offs

- [风险] 测试依赖现有实现行为 → 缓解：测试断言与 PRD01 验收标准对齐
- [风险] `*.localhost`/`*.local`/`*.invalid` 可能在未来 Python 版本中被 `ipaddress` 模块原生支持 → 缓解：当前自定义检测已覆盖
