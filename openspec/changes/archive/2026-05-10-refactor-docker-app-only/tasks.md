## 1. Docker Compose Refactoring

- [x] 1.1 Update `docker-compose.yml` to remove infrastructure services and add application services (`api`, `worker`, `web`).
- [x] 1.2 Configure `extra_hosts` and environment mapping for application services to use host infrastructure.
- [x] 1.3 Update `docker-compose.prod.yml` to maintain full-stack capability (including infra containers).

## 2. Documentation & Verification

- [x] 2.1 Update `README.md` to clarify that `docker compose up` starts the apps and requires host services.
- [x] 2.2 Verify `docker compose config` is valid.
- [x] 2.3 Verify `docker compose build` succeeds with the unified `Dockerfile`.
