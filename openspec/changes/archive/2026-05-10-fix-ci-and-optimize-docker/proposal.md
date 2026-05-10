## Why

The current CI pipeline is failing due to outdated tests that still expect legacy password-based authentication, which has been removed. Additionally, the Docker setup contains redundant dependencies and can be optimized for better performance and smaller image sizes.

## What Changes

- **Update CI Workflow**: Ensure `PYTHONPATH` is correctly configured to include `apps/api`, `apps/worker`, and `packages/shared`.
- **Refactor Authentication Tests**: Remove or update tests in `apps/api/tests/test_auth.py` and `test_admin.py` that rely on password-based login/registration.
- **Docker Optimization**:
    - Move `ffmpeg` and `ffprobe` to a more specific stage if possible, or ensure they are only installed once in the base.
    - Consolidate `RUN` commands to reduce layers.
    - Use more specific `COPY` commands to avoid pulling in unnecessary files.
    - Remove redundant dependencies from `requirements.txt` if any.
- **Refine Docker Compose**: Clean up `docker-compose.yml` to remove unnecessary configurations.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `user-auth`: Update to reflect GitHub OAuth as the sole authentication mechanism.
- `project-runtime-foundation`: Optimize Docker and CI runtime configurations.

## Impact

- **CI/CD**: Improved reliability and faster feedback.
- **Deployment**: Smaller Docker images and faster build times.
- **Security**: Removal of legacy authentication code paths.
