## 1. Fix Backend Tests

- [x] 1.1 Remove legacy password auth tests from `apps/api/tests/test_auth.py`
- [x] 1.2 Remove legacy password auth tests from `apps/api/tests/test_admin.py`
- [x] 1.3 Verify backend tests pass locally with correct `PYTHONPATH`

## 2. CI Workflow & Dependencies

- [x] 2.1 Update `.github/workflows/ci.yml` to set `PYTHONPATH` explicitly
- [x] 2.2 Add `pytest-asyncio` and `pytest-mock` if needed for OAuth testing
- [x] 2.3 Fix the Docker build error by correcting paths in `Dockerfile`

## 3. Docker Optimization

- [x] 3.1 Optimize root `Dockerfile` to consolidate `RUN` layers and fix requirements copy
- [x] 3.2 Refine `COPY` commands to leverage build cache and reduce image size
- [x] 3.3 Clean up `docker-compose.yml` to remove redundant configurations

## 4. Verification

- [x] 4.1 Run `pytest` locally with the full suite
- [x] 4.2 Build Docker images for `api`, `worker`, and `web` targets
- [x] 4.3 Verify the system starts up correctly using `docker-compose.yml`
