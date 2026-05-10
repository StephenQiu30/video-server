## 1. Backend Integration

- [x] 1.1 Add `StaticFiles` mounting and 404 handler for SPA routing in `apps/api/app/main.py`
- [x] 1.2 Ensure `api` routes are correctly prefixed to avoid conflicts

## 2. Docker Refactor

- [x] 2.1 Update `Dockerfile` to remove `nginx` stage and copy `dist` to `api` stage
- [x] 2.2 Update `docker-compose.yml` and `docker-compose.prod.yml` to remove `web` service

## 3. Verification

- [/] 3.1 Build Docker images and run `docker compose up`
- [ ] 3.2 Verify both API and UI are accessible on the same port (e.g., 8000)
