## Context

The user pointed out that Nginx is unnecessary for a non-production project. Consolidating the web server into the FastAPI application follows the MVP principle and reduces container overhead.

## Goals / Non-Goals

**Goals:**
- Remove Nginx from the Docker stack.
- Serve the frontend UI from the FastAPI backend.
- Maintain SPA routing support.

**Non-Goals:**
- Optimizing for high-concurrency static file delivery (not needed for local MVP).

## Decisions

### 1. Serve Static Files via FastAPI
Rationale: Easiest way to consolidate services.
Implementation: Use `fastapi.staticfiles.StaticFiles` mounted at `/`.

### 2. SPA Routing Support
Rationale: SPA (React/Vite) expects the server to return `index.html` for any unknown routes so the client-side router can handle them.
Implementation: Add a catch-all route or a 404 exception handler that serves `index.html` if the request is not for an `/api` endpoint.

### 3. Dockerfile Refactor
- Keep `web-builder` stage to build the React app.
- API stage copies `/app/apps/web/dist` to `/app/static`.

## Risks / Trade-offs

- **[Risk]** API routes and static file routes might conflict.
  - **Mitigation**: Ensure API routes are prefixed with `/api` and defined before mounting static files.
