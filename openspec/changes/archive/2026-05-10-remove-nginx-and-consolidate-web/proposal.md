## Why

Nginx is unnecessary for a local MVP that is not intended for production deployment. Serving static files directly from the FastAPI backend simplifies the architecture, reduces the number of running containers, and minimizes resource consumption.

## What Changes

- **FastAPI Integration**: Mount `StaticFiles` in `apps/api/app/main.py` to serve the frontend `dist` folder.
- **Dockerfile Refactor**: 
    - Remove the `web` and Nginx stages.
    - Update the `api` stage to copy the built `dist` from the `web-builder` stage.
- **Docker Compose Update**: Remove the `web` service and ensure the `api` service handles both API requests and frontend delivery.
- **Cleanup**: Remove any Nginx-specific configurations.

## Capabilities

### New Capabilities
- None

### Modified Capabilities
- `project-runtime-foundation`: Consolidate web serving into the API runtime.

## Impact

- **Infrastructure**: One less container to manage and start.
- **Performance**: Slight increase in API memory usage to serve static files, but offset by the removal of the Nginx container.
- **Development**: Simplifies local testing of the full stack in Docker.
