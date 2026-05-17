## Why

Users frequently copy video sharing messages directly from mainstream mobile apps (such as Douyin, Bilibili, and Kuaishou). These messages contain excess promotional text, emojis, and sharing descriptors around the actual URL (e.g., `【小猫的作品】https://v.douyin.com/iJxxqxx/ 复制链接即可查看...`).

Currently, passing this raw text block directly to the backend parsing and download engine causes parsing to fail. To provide a professional, seamless experience, the platform must automatically sanitize the input link, extract the clean URL, and adapt the download worker configurations (including browser cookie integration) to handle high-resolution downloads from these mainstream platforms.

---

## What Changes

1. **Input Link Sanitization & Parsing**:
   - Implement an automated URL extraction helper in the API layer. Before parsing the URL, extract the first valid HTTP/HTTPS URL from any input text block.
   - Clean up trailing query parameters that might trigger platform anti-scraping or tracing rules if necessary.

2. **Downloader Engine Configurations & Upgrades**:
   - Ensure the `yt-dlp` library in the virtual environment is updated to maintain alignment with platform signature updates.
   - Fully integrate the local browser cookie sharing feature (`YTDLP_COOKIES_FROM_BROWSER`) to ensure compatibility with high-resolution (1080p, 4K) Bilibili/YouTube downloads that require active sessions.

3. **Compose Path Fix (Chore)**:
   - Fix the incorrect `docker-compose.yml` path in `scripts/start.sh` (changing `infra/docker/docker-compose.yml` to the root `docker-compose.yml`).

---

## Capabilities

### New Capabilities
- `link-sanitizer`: A utility module to automatically extract and sanitize URLs from rich-text shared video descriptions, allowing users to paste raw mobile share texts directly.

### Modified Capabilities
- `video-download-tasks`: Modify the URL parsing requirement to utilize the link sanitizer during input validation.

---

## Impact

- **apps/api**:
  - `app/services/download_adapter.py`: Integrate input sanitization in the `parse` method.
- **scripts/start.sh**:
  - Update paths pointing to `infra/docker/docker-compose.yml` to use the root `docker-compose.yml` instead.
