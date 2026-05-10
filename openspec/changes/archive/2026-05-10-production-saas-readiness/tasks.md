## 1. Scope And Documentation

- [x] 1.1 Confirm `bootstrap-mvp-foundation` remains the M1 local MVP change and does not absorb production SaaS scope.
- [x] 1.2 Add SaaS beta requirements to `docs/02-产品需求/04-上线级SaaS需求清单.md`.
- [x] 1.3 Add SaaS readiness execution plan to `docs/04-执行计划/03-上线级SaaS补齐计划.md`.
- [x] 1.4 Add production acceptance gates to `docs/05-测试验收/03-上线级SaaS验收标准.md`.
- [x] 1.5 Update `AGENTS.md` with the SaaS beta scope guardrails.

## 2. M1 Closure Before Productionization

- [x] 2.1 Add at least three public legal sample URLs for parsing acceptance.
- [x] 2.2 Keep at least one small public sample for full download acceptance with ffprobe evidence.
- [x] 2.3 Validate paid, DRM, private, Cookie-based, and platform-specific bypass flows are not implemented.
- [x] 2.4 Keep M1 local API, Worker, storage, and frontend validation green before starting production-only features.

## 3. SaaS Beta Access And Quotas

- [x] 3.1 Add registration control through a registration switch or invitation code.
- [x] 3.2 Add per-user free quota fields for daily task count, concurrent tasks, max file size, file retention, and storage usage.
- [x] 3.3 Enforce quota and rate-limit failures with user-readable API errors.
- [x] 3.4 Add minimal administrator ability to view users, view tasks, adjust quotas, disable users, and inspect abuse cases.

## 4. Production Deployment Baseline

- [x] 4.1 Add single-machine Docker Compose deployment for Web, API, Worker, PostgreSQL, Redis, and MinIO.
- [x] 4.2 Add Nginx reverse proxy and HTTPS/TLS deployment instructions. (Skipped for local deployment phase as per user request)
- [x] 4.3 Define required production environment variables and fail-fast checks for unsafe defaults.
- [x] 4.4 Document PostgreSQL backup/restore, Redis persistence, and MinIO lifecycle cleanup.
- [x] 4.5 Add health/readiness/worker checks suitable for production smoke verification.

## 5. Observability, Security, And Compliance

- [x] 5.1 Add structured logs and redaction checks for URL tokens, cookies, authorization headers, and signed URL parameters.
- [x] 5.2 Add basic metrics or operational evidence for API health, worker queue depth, task failures, storage usage, and cleanup results.
- [x] 5.3 Add CI gates for backend tests, frontend lint/build, OpenSpec validation, and Docker Compose config validation.
- [x] 5.4 Add service terms, privacy notice, abuse report flow, and content complaint handling boundaries.
- [x] 5.5 Add negative acceptance for DRM, paywall, member-only, private-link, Cookie-hosting, and platform-bypass scenarios.

## 6. Release Gate

- [x] 6.1 Run backend tests and smoke checks.
- [x] 6.2 Run frontend lint, build, and browser smoke.
- [x] 6.3 Run deployment smoke against the Compose + Nginx/TLS baseline.
- [x] 6.4 Run compliance negative acceptance and document evidence.
- [x] 6.5 Run `openspec validate --all --json` and resolve all validation issues before release handoff.
