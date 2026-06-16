# Tasks: PLAN12 Global Response & Exception Handling

- [ ] 1. Update `request_context_middleware` to store `request_id` in `request.state`
- [ ] 2. Update `failure_response` to accept and include `request_id`
- [ ] 3. Update all exception handlers to pass `request_id` from `request.state`
- [ ] 4. Update `test_request_context_middleware.py` to verify `request.state.request_id`
- [ ] 5. Update `test_api_contract.py` to verify `request_id` in failure responses
- [ ] 6. Run full test suite and confirm all tests pass
