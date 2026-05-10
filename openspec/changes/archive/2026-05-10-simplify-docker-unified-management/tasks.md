## 1. File Consolidation & Cleaning

- [x] 1.1 Create root `.dockerignore` to optimize build context.
- [x] 1.2 Move and merge existing Dockerfiles into a single root `Dockerfile`.
- [x] 1.3 Remove old `infra/docker` directory.

## 2. Docker Compose Rationalization

- [x] 2.1 Create root `docker-compose.yml` for infrastructure (DB, Redis, MinIO).
- [x] 2.2 Create root `docker-compose.prod.yml` for full stack deployment.
- [x] 2.3 Ensure both files correctly reference the root `.env` file.

## 3. GitHub Actions & Script Updates

- [x] 3.1 Update CI/CD workflows to reflect new Docker paths (if any).
- [x] 3.2 Update `README.md` with new "Getting Started" commands.

## 4. Verification

- [x] 4.1 Verify `docker compose up -d` starts infrastructure successfully.
- [x] 4.2 Verify `docker compose -f docker-compose.prod.yml build` succeeds for all services.
- [x] 4.3 Perform end-to-end smoke test using Docker environment.
