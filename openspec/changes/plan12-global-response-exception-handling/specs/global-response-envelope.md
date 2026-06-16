# Spec: Global Failure Response Envelope

## Current State

`failure_response` returns:
```json
{
  "success": false,
  "error": {
    "code": "error_code",
    "message": "error message",
    "details": null
  }
}
```

## Target State

`failure_response` returns:
```json
{
  "success": false,
  "error": {
    "code": "error_code",
    "message": "error message",
    "details": null
  },
  "request_id": "hex-uuid"
}
```

## Contract

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `success` | `bool` | always `false` for failure | Indicates failure |
| `error.code` | `str` | yes | Machine-readable error code from `ErrorCode` enum |
| `error.message` | `str` | yes | Human-readable error message (safe for user display) |
| `error.details` | `any` | nullable | Validation details or additional context |
| `request_id` | `str` | yes | Request trace ID, sourced from `X-Request-ID` header or auto-generated |

## Backward Compatibility

- Success responses are unchanged (no envelope wrapping).
- Failure response adds `request_id` as a new top-level field — additive, non-breaking for consumers that ignore unknown fields.
- `X-Request-ID` response header continues to be set by middleware.
