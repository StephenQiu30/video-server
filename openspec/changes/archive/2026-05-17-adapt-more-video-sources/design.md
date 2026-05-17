## Context

Mainstream video sharing apps (Bilibili, Douyin, Kuaishou, etc.) generate rich text blocks when users copy a share link. These text blocks mix emojis, descriptive text, and promotional phrases around the actual video URL.

Currently, our backend's `download_adapter` fails when users copy-paste these entire text blocks. Additionally, `scripts/start.sh` attempts to invoke docker-compose using incorrect nested paths (`infra/docker/docker-compose.yml`), making `npm start` unusable.

---

## Goals / Non-Goals

**Goals:**
- Natively support pasting raw mobile share copy-pastes for Bilibili, Douyin, and Kuaishou.
- Automatically strip any prefix/suffix decorators, emojis, and Chinese text, keeping only the clean video URL.
- Fix all docker-compose invocations in `scripts/start.sh` to reference the root `docker-compose.yml` and `docker-compose.prod.yml`.

**Non-Goals:**
- Writing complex HTML scrapers or custom platform decryption engines (which would violate our MVP simplicity). We continue to rely on the latest upgraded `yt-dlp` core.
- Accepting multiple URLs in a single share block; we will only extract the first valid URL.

---

## Decisions

### Decision 1: Regex-Based Input Sanitizer in `app/services/download_adapter.py`
- **Choice**: Implement a regex pattern in the python parsing service to extract the first valid HTTP/HTTPS URL from any input string.
- **Rationale**: Keeps the implementation simple and clean, avoids pulling in heavy HTML parsing dependencies, and runs extremely fast.
- **Alternatives Considered**: 
  - *Frontend sanitization*: We could sanitize in the Vite client, but sanitizing at the API level ensures robustness for API requests and standard error reporting.

### Decision 2: Resolve Compose File Paths in `scripts/start.sh`
- **Choice**: Update all `-f` path parameters from `infra/docker/docker-compose.yml` to `docker-compose.yml` (and production equivalents).
- **Rationale**: Aligns the startup script with the actual root location of the docker compose files.

---

## Risks / Trade-offs

- **[Risk] Multiple URLs in pasted text** → If a user pastes a text block containing multiple URLs, the regex will extract and process the first one.
  - *Mitigation*: This is standard practice in messaging applications and matches typical user expectation for single-item sharing.
