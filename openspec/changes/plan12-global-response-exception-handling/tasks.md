# Tasks: PLAN12 Global Response & Exception Handling

- [x] 1. Update `request_context_middleware` to store `request_id` in `request.state`
- [x] 2. Update `failure_response` to accept and include `request_id`
- [x] 3. Update all exception handlers to pass `request_id` from `request.state`
- [x] 4. Update `test_request_context_middleware.py` to verify `request.state.request_id`
- [x] 5. Update `test_api_contract.py` to verify `request_id` in failure responses
- [x] 6. Run full test suite and confirm all tests pass
