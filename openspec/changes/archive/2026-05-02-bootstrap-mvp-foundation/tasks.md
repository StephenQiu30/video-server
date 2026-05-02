## 1. Project Runtime Foundation

- [x] 1.1 Create monorepo directories: `apps/web`, `apps/api`, `apps/worker`, `packages/shared`, and `infra/docker`.
- [x] 1.2 Add root README/startup notes for the M1 local workflow and Docker deployment workflow.
- [x] 1.3 Add local, Docker, and production environment templates covering API, worker, PostgreSQL, Redis, MinIO, JWT, and download limit settings.
- [x] 1.4 Add Docker Compose services for web, api, worker, PostgreSQL, Redis, and MinIO.
- [x] 1.5 Verify local stack service names, networks, volumes, and health checks are documented.

## 2. Web App Foundation

- [x] 2.1 Initialize `apps/web` with React + Umi + Ant Design Pro.
- [x] 2.2 Add routes and layout for login/register, download workspace, task list, and task detail.
- [x] 2.3 Add API client scaffolding for auth, parse, task, cancel, and download-link endpoints.
- [x] 2.4 Add user-facing compliance copy for authorized public or owned content only.

## 3. API Foundation

- [x] 3.1 Initialize `apps/api` with FastAPI + Python 3.12.
- [x] 3.2 Add PostgreSQL models or migrations for users, download tasks, task events, and stored files.
- [x] 3.3 Implement JWT registration, login, current-user, and auth dependency.
- [x] 3.4 Implement parse, create-task, list-tasks, get-task, cancel-task, and download-link API contracts.
- [x] 3.5 Add structured error responses for unsupported platform, parse failure, limit exceeded, timeout, canceled, and storage failure.

## 4. Worker And Download Engine

- [x] 4.1 Initialize `apps/worker` with RQ worker entrypoint and shared configuration.
- [x] 4.2 Add yt-dlp adapter for metadata extraction and selected-format download.
- [x] 4.3 Add FFmpeg / ffprobe integration for merge, probe, and output validation.
- [x] 4.4 Enforce resource limits: 2GB max file size, 2 hour max runtime, global concurrency 2, per-user concurrency 1.
- [x] 4.5 Update task states through queued, running, succeeded, failed, and canceled.

## 5. Object Storage Delivery

- [x] 5.1 Configure private MinIO / S3 bucket `video-downloads`.
- [x] 5.2 Store objects using `users/{user_id}/tasks/{task_id}/{filename}` keys.
- [x] 5.3 Generate backend-authorized presigned download URLs with 15 minute TTL.
- [x] 5.4 Add 24 hour retention cleanup for stored task outputs.
- [x] 5.5 Ensure bucket is not publicly readable by default.

## 6. Verification And Documentation

- [x] 6.1 Add smoke tests or scripts covering auth, parse, task creation, task query, and download-link flow.
- [x] 6.2 Add at least three public legal sample URLs for parsing acceptance and one small sample for download acceptance.
- [x] 6.3 Validate that paid, DRM, private, Cookie-based, and platform-specific bypass flows are not implemented.
- [x] 6.4 Update docs with actual startup commands, environment defaults, and validation evidence.
- [x] 6.5 Run `openspec validate --all` and resolve all validation issues before implementation handoff.
