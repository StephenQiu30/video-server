## Context

The project recently moved to GitHub OAuth as the primary authentication method, but the test suite still contains legacy tests for password-based login and registration, causing CI failures. Additionally, the CI environment lacks proper path configuration, and the Docker setup can be optimized for better performance and smaller images.

## Goals / Non-Goals

**Goals:**
- Fix CI pipeline stability.
- Remove legacy authentication tests.
- Optimize root `Dockerfile` and `docker-compose.yml`.
- Ensure all core components have minimal necessary dependencies in their final Docker images.

**Non-Goals:**
- Adding new authentication providers.
- Refactoring the core business logic of the video downloader.
- Changing the database schema.

## Decisions

### 1. Remove Legacy Auth Tests
Rationale: The project has pivoted to GitHub OAuth. Legacy tests are no longer relevant and cause noise.
Alternatives: Mocking legacy auth, but that adds maintenance burden for a feature that is being removed.

### 2. Explicit PYTHONPATH in CI
Rationale: Ensures tests can always find the `app` and `worker` modules regardless of the working directory or environment setup.
Alternatives: Installing the apps as editable packages, but that's more complex for a simple monorepo.

### 3. Docker Multi-stage Optimization
- **Consolidate RUN commands**: Use `apt-get update && ... && rm -rf /var/lib/apt/lists/*` in a single line to reduce layer size.
- **Selective COPY**: Only copy `requirements.txt` first to leverage Docker cache for dependency installation.
- **Target-Specific Dependencies**: Ensure `ffmpeg` is available where needed (Worker) but minimize its impact on the API image if possible (though API currently needs it for readiness checks).

### 4. CI Dependencies
Add `pytest-asyncio` or other missing plugins explicitly to `requirements.txt` or CI installation step if they are missing.

## Risks / Trade-offs

- **[Risk]** Removing legacy tests might accidentally remove coverage for some shared utilities.
  - **Mitigation**: Verify that shared utilities are covered by other tests or add specific unit tests for them.
- **[Trade-off]** Keeping `ffmpeg` in the base image for API readiness check makes the API image larger.
  - **Mitigation**: The size impact of `ffmpeg-slim` is acceptable for the convenience of a shared base, but we will use `python-slim` to keep it as small as possible.
