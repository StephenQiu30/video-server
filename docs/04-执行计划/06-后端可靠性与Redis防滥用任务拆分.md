---
layer: Plan
doc_no: "06"
audience:
  - PM
  - Dev
  - QA
  - Ops
feature_area: backend-reliability
purpose: "拆分 Worker 类型化流水线、任务可靠性、Redis 接口限流、登录注册锁、全局异常处理与统一接口响应封装的执行任务。"
canonical_path: "docs/04-执行计划/06-后端可靠性与Redis防滥用任务拆分.md"
status: draft
version: "0.1.0"
owner: "StephenQiu30"
inputs:
  - "docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md"
outputs:
  - "GitHub issue 拆分建议"
  - "TDD 执行顺序"
triggers:
  - "准备执行 Worker 可靠性重构"
  - "准备执行 Redis 限流与登录注册锁"
  - "准备治理 API 错误响应契约"
downstream:
  - "GitHub issues"
  - "Feature PR"
---

# 后端可靠性与 Redis 防滥用任务拆分

## 1. 背景

本计划承接 `docs/03-架构设计/06-后端可靠性与Redis防滥用设计.md`，用于把 Worker 类型化流水线、Redis 防滥用和 API 错误响应契约治理拆成可执行、可测试、可建 issue 的任务。

## 2. 目标

- 将 Worker 重构拆成小 issue，避免一次性大改。
- 每个 issue 都有明确 TDD 红灯测试、实现边界和验收标准。
- Redis 限流和登录注册锁作为同一阶段的安全基线纳入计划。
- 全局异常处理和统一失败响应作为 API 合同基线纳入计划。
- 保持一个完整 feature PR，PR 关联并关闭本轮 issues。

## 3. 非目标

- 不在本计划中实现 P2 数据库迁移治理。
- 不拆前端 issue。
- 不把真实平台 smoke 作为默认 CI。
- 不引入新的任务队列或监控服务端。

## 4. Epic 总览

| Epic | 目标 | 优先级 | 类型 | 建议 PR |
| --- | --- | --- | --- | --- |
| E1 Worker Domain 类型基础 | Enum + DTO 固化内部边界 | P1 | refactor/test | PR-A |
| E2 下载执行器与媒体校验拆分 | 下载、ffprobe、产物解析模块化 | P1 | refactor/test | PR-A |
| E3 失败分类与幂等边界 | 统一失败码、重复入队、取消边界 | P1 | reliability/test | PR-A |
| E4 AI 后处理隔离 | AI 失败不污染主任务成功态 | P1 | ai/test | PR-A |
| E5 Redis 接口限流 | `/api/parse` 与 `/api/tasks` 多实例共享限流 | P1 | security/test | PR-B |
| E6 登录注册锁 | 登录失败锁与注册防滥用 | P1 | security/test | PR-B |
| E7 全局异常与统一响应 | 统一失败结构，保留成功响应兼容 | P1 | api-contract/test | PR-B |

建议分成两个 feature PR：

- **PR-A：Worker 类型化流水线与任务可靠性**，关闭 E1-E4 issues。
- **PR-B：Redis 限流、登录注册锁与 API 错误封装**，关闭 E5-E7 issues。

如果需要更快交付，也可以合并为一个 PR，但风险是 reviewer 同时审 Worker 重构和安全策略，审查成本更高。

## 5. Issue 拆分

### Issue 1：Worker Domain 枚举与 DTO 基础

建议标题：`[P1][backend][worker] Worker Domain 枚举与 DTO 基础`

任务类型：`type:backend`, `type:test`, `workflow:tdd`, `priority:P1`

验收标准：

- 新增 `worker/domain.py`。
- 定义 `WorkerStage`、`WorkerFailureCode`、`AIProcessStatus`。
- 定义 `WorkerContext`、`DownloadArtifact`、`StoredArtifact`、`FailureInfo`、`AIProcessResult`。
- DTO 单元测试覆盖默认字段、不可变性和枚举值。

### Issue 2：下载执行器与媒体校验模块化

建议标题：`[P1][backend][worker] 下载执行器与媒体校验模块化`

任务类型：`type:backend`, `workflow:tdd`, `priority:P1`

验收标准：

- 新增 `worker/download_runner.py`。
- 新增 `worker/media_probe.py`。
- `_resolve_output_path`、媒体工具检查、ffprobe 校验迁移到对应模块。
- 原有 worker 测试迁移或补充到模块级测试。
- `jobs.py` 对下载和媒体校验只做调用，不保留细节实现。

### Issue 3：Worker 失败分类与任务幂等边界

建议标题：`[P1][backend][reliability] Worker 失败分类与任务幂等边界`

任务类型：`type:backend`, `type:test`, `priority:P1`

验收标准：

- 新增 `worker/failures.py`。
- 异常统一转换为 `FailureInfo`。
- 成功任务重复入队时跳过。
- 取消任务不下载。
- 上传后取消会删除已上传对象。
- 失败码覆盖格式不可用、文件过大、平台限流、平台受限、存储失败、媒体工具缺失。

### Issue 4：AI 后处理流水线隔离

建议标题：`[P1][backend][ai] AI 后处理流水线隔离`

任务类型：`type:backend`, `type:test`, `priority:P1`

验收标准：

- 新增 `worker/ai_pipeline.py`。
- AI 成功返回 `AIProcessResult(status=completed)`。
- AI 配置缺失返回 `AIProcessResult(status=skipped)`。
- AI 失败返回 `AIProcessResult(status=failed)`，主任务仍保持 `succeeded`。
- 音频临时文件始终清理。

### Issue 5：Redis 接口限流基线

建议标题：`[P1][backend][security] Redis 接口限流基线`

任务类型：`type:backend`, `type:compliance`, `workflow:tdd`, `priority:P1`

验收标准：

- 扩展 `app/services/rate_limit.py`，新增 `RateLimitScope`、`RateLimitPolicy`、`RateLimitResult`。
- 新增 `RedisRateLimiter`。
- `/api/parse` 使用 Redis-backed 限流，local/testing 可 fallback 到内存。
- `/api/tasks` 创建任务使用 per-user 限流。
- Redis 不可用 fallback 行为有测试覆盖。
- 429 错误使用 `AppError("rate_limited", ..., 429)`。

### Issue 6：登录注册失败锁与防爆破保护

建议标题：`[P1][backend][security] 登录注册失败锁与防爆破保护`

任务类型：`type:backend`, `type:compliance`, `workflow:tdd`, `priority:P1`

验收标准：

- 新增 `app/services/auth_lock.py`。
- 登录失败按 email hash 和 IP 计数。
- 登录成功清除 email hash 锁。
- 注册按 IP 限制，不按 email 锁死。
- 锁定时返回 `AppError("auth_locked", ..., 429)`。
- 错误文案不泄露账号是否存在。

### Issue 7：全局异常处理与统一失败响应封装

建议标题：`[P1][backend][api-contract] 全局异常处理与统一失败响应封装`

任务类型：`type:backend`, `type:api-contract`, `workflow:tdd`, `priority:P1`

验收标准：

- 新增或扩展 `app/core/responses.py`。
- `AppError` 返回 `success=false` 和统一 `error` 对象。
- `HTTPException(401/403/404)` 被转换为统一失败响应。
- `RequestValidationError` 返回 `error.code=validation_error`。
- 未知异常返回 `error.code=internal_error`，不泄露堆栈和敏感信息。
- 本 issue 不改变现有成功响应结构。

## 6. TDD 执行顺序

1. `test:` Worker Domain 和 DTO 单元测试。
2. `impl:` Worker Domain 和 DTO 最小实现。
3. `test:` 下载执行器、媒体校验、失败分类、幂等边界测试。
4. `impl:` 拆分 Worker 模块，并保持 `jobs.py` 行为等价。
5. `refactor:` 收缩 `jobs.py`，清理旧 helper。
6. `test:` Redis 限流与 auth lock 红灯测试。
7. `impl:` Redis 限流、任务创建限流、登录注册锁。
8. `test:` 全局异常与统一失败响应红灯测试。
9. `impl:` 全局异常 handlers 与统一失败响应封装。
10. `docs:` 更新验收标准和运维合规边界。

## 7. 验收门禁

- 每个 issue 都有至少一个红灯测试证据。
- `npm test` 通过。
- `git diff --check` 通过。
- Docker config 校验通过。
- PR body 包含 Test-first Evidence、Tests added、Commands run、Result、Agent Usage 和 Reviewer Checklist。
- PR body 使用 `Closes #<issue>` 关联对应 issue。

## 8. 风险与边界

- Worker 模块拆分应分阶段提交，避免一次性移动导致 review 困难。
- Redis 限流在生产环境建议 fail-open，但必须记录日志；如果后续业务要求强风控，可单独改为 fail-closed。
- 登录失败锁要避免账号枚举，错误提示应保持泛化。
- `/api/tasks` 限流不能替代已有配额，二者需要同时存在。
- 成功响应统一 envelope 不在本阶段执行，否则会扩大前端联调和回归范围。

## 9. 待确认问题

- 是否接受分成 PR-A 和 PR-B 两个 feature PR。
- Redis 限流生产默认是否 fail-open。
- 登录失败锁是否同时启用 email hash 和 IP 维度。
- 本阶段是否确认只统一失败响应，成功响应 envelope 留到前端 API client 协同阶段。

## 10. 变更记录

| 日期 | 作者 | 版本 | 变更说明 |
| --- | --- | --- | --- |
| 2026-05-23 | StephenQiu30 | 0.1.0 | 初始化后端可靠性、Redis 防滥用、全局异常与统一失败响应任务拆分 |
