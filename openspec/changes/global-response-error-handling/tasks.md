## 1. OpenSpec Change Artifacts

- [ ] 1.1 创建 `openspec/changes/global-response-error-handling/proposal.md`
- [ ] 1.2 创建 `openspec/changes/global-response-error-handling/design.md`
- [ ] 1.3 创建 `openspec/changes/global-response-error-handling/specs/global-error-model/spec.md`
- [ ] 1.4 创建 `openspec/changes/global-response-error-handling/specs/exception-handlers/spec.md`
- [ ] 1.5 创建 `openspec/changes/global-response-error-handling/specs/request-id/spec.md`
- [ ] 1.6 创建 `openspec/changes/global-response-error-handling/tasks.md`

## 2. Request ID 集成

- [ ] 2.1 修改 `apps/api/app/middleware/request_context.py`，将 request_id 存储到 request.state
- [ ] 2.2 验证 request_id 在 request.state 中可用

## 3. Failure Envelope 增强

- [ ] 3.1 修改 `apps/api/app/core/responses.py`，failure_response 函数增加 request_id 参数
- [ ] 3.2 验证 failure_response 返回包含 request_id 的响应

## 4. Exception Handlers 更新

- [ ] 4.1 修改 `app_error_handler`，从 request.state 获取 request_id 并传递
- [ ] 4.2 修改 `http_exception_handler`，从 request.state 获取 request_id 并传递
- [ ] 4.3 修改 `validation_exception_handler`，从 request.state 获取 request_id 并传递
- [ ] 4.4 修改 `unhandled_exception_handler`，从 request.state 获取 request_id 并传递

## 5. 契约测试

- [ ] 5.1 创建 `apps/api/tests/test_error_contract.py`
- [ ] 5.2 编写 AppError 契约测试
- [ ] 5.3 编写 HTTPException 契约测试
- [ ] 5.4 编写 RequestValidationError 契约测试
- [ ] 5.5 编写未知异常契约测试
- [ ] 5.6 编写 Request ID 来源测试

## 6. 推广 Specs 到 Baseline

- [ ] 6.1 推广 `global-error-model` spec 到 `openspec/specs/global-error-model/spec.md`
- [ ] 6.2 推广 `exception-handlers` spec 到 `openspec/specs/exception-handlers/spec.md`
- [ ] 6.3 推广 `request-id` spec 到 `openspec/specs/request-id/spec.md`

## 7. 验证

- [ ] 7.1 运行 `pytest apps/api/tests/test_error_contract.py -v`，全部通过
- [ ] 7.2 运行 `pytest apps/api/tests/ -v`，无回归
- [ ] 7.3 运行 `bash scripts/validate-repository.sh`，通过
- [ ] 7.4 审阅 PRD07、PLAN12 与设计文档，确认一致性

## 8. 文档更新

- [ ] 8.1 更新 `docs/plans/12-全局响应与异常处理计划.md` 状态从 `draft` 到 `accepted`
