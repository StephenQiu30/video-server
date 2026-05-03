## 1. OpenSpec And Documentation

- [x] 1.1 Add focused M1 requirements for signed API download proxy, task retry/events, and native Ant Design Pro workspace.
- [x] 1.2 Sync `AGENTS.md` and M1 docs so local single-user/no-login is the active M1 rule.

## 2. Backend Download And Task Flow

- [x] 2.1 Return short-lived backend signed download URLs from `download-link` and add streaming download endpoint.
- [x] 2.2 Add task events API and retry API that creates a new task from a failed/canceled/expired task.
- [x] 2.3 Add stale active-task timeout reconciliation and clearer worker failure classification.

## 3. Frontend MVP Workspace

- [x] 3.1 Replace over-designed pages with Ant Design Pro / Pro Components native layouts.
- [x] 3.2 Wire frontend downloads to the backend signed URL, show task events, and expose retry actions.

## 4. Acceptance

- [x] 4.1 Update smoke scripts for signed proxy download, retry/events, and negative cases.
- [x] 4.2 Run OpenSpec, backend, smoke, frontend lint/build, and browser-oriented checks.
