# Design: PLAN12 Global Response & Exception Handling

## Architecture

### Request Flow

```
Request → request_context_middleware → route handler → Response
                              ↓ (on exception)
                      exception handler → failure_response → JSONResponse
```

### Components

1. **request_context_middleware** — extracts/generates `request_id`, stores in `request.state.request_id`, sets response header.
2. **failure_response** — builds unified failure envelope dict with `request_id`.
3. **Exception handlers** — read `request_id` from `request.state` and pass to `failure_response`.

### Design Decisions

- `request_id` is stored on `request.state.request_id` for exception handlers to access.
- `failure_response` accepts `request_id` as a parameter (default `None`).
- Exception handlers receive `Request` and can read `request.state.request_id`.
- Success responses are NOT wrapped — this preserves backward compatibility with existing API consumers.

## Data Flow

### Middleware
```python
request_id = request.headers.get("X-Request-ID") or uuid4().hex
request.state.request_id = request_id  # NEW: store for exception handlers
response.headers["X-Request-ID"] = request_id  # EXISTING
```

### failure_response
```python
def failure_response(code, message, details=None, request_id=None):
    envelope = {"success": False, "error": {"code": code, "message": message, "details": details}}
    if request_id:
        envelope["request_id"] = request_id
    return envelope
```

### Exception handlers
```python
async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content=failure_response(exc.code, exc.message, exc.details, getattr(request.state, "request_id", None)),
    )
```
