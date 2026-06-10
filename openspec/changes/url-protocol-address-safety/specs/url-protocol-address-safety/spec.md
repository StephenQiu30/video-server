## ADDED Requirements

### Requirement: API endpoints MUST reject dangerous URLs
The `/api/tasks` and `/api/parse` endpoints SHALL reject URLs targeting localhost, private IPs, loopback addresses, link-local addresses, multicast addresses, reserved addresses, and unspecified addresses with HTTP 422 and error code `invalid_url`.

#### Scenario: POST /api/tasks with localhost URL
- **WHEN** client sends `POST /api/tasks` with `{"url": "http://localhost/video"}`
- **THEN** response status MUST be 422
- **AND** response body error code MUST be `invalid_url`

#### Scenario: POST /api/tasks with private IP
- **WHEN** client sends `POST /api/tasks` with `{"url": "http://10.0.0.1/video"}`, `{"url": "http://172.16.0.1/video"}`, or `{"url": "http://192.168.1.1/video"}`
- **THEN** response status MUST be 422
- **AND** response body error code MUST be `invalid_url`

#### Scenario: POST /api/tasks with loopback IP
- **WHEN** client sends `POST /api/tasks` with `{"url": "http://127.0.0.1/video"}`
- **THEN** response status MUST be 422
- **AND** response body error code MUST be `invalid_url`

#### Scenario: POST /api/tasks with non-http scheme
- **WHEN** client sends `POST /api/tasks` with `{"url": "ftp://example.com/video"}` or `{"url": "file:///etc/passwd"}`
- **THEN** response status MUST be 422

#### Scenario: POST /api/tasks with empty URL
- **WHEN** client sends `POST /api/tasks` with `{"url": ""}`
- **THEN** response status MUST be 422

#### Scenario: POST /api/tasks with plain text
- **WHEN** client sends `POST /api/tasks` with `{"url": "not a url at all"}`
- **THEN** response status MUST be 422
- **AND** response body error code MUST be `invalid_url`

#### Scenario: POST /api/tasks with public URL succeeds
- **WHEN** client sends `POST /api/tasks` with `{"url": "https://www.bilibili.com/video/BV1xx411c7mD"}`
- **THEN** response status MUST be 201

#### Scenario: POST /api/parse with localhost URL
- **WHEN** client sends `POST /api/parse` with `{"url": "http://localhost/video"}`
- **THEN** response status MUST be 422
- **AND** response body error code MUST be `invalid_url`

#### Scenario: POST /api/parse with private IP
- **WHEN** client sends `POST /api/parse` with `{"url": "http://192.168.1.1/video"}`
- **THEN** response status MUST be 422
- **AND** response body error code MUST be `invalid_url`

#### Scenario: POST /api/parse with reserved IP
- **WHEN** client sends `POST /api/parse` with `{"url": "http://0.0.0.0/video"}`
- **THEN** response status MUST be 422
- **AND** response body error code MUST be `invalid_url`

### Requirement: URL normalizer MUST reject multicast and IPv6 private addresses
The `normalize_user_url()` function SHALL reject multicast IPs (224.0.0.0/4), IPv6 private addresses (fc00::/7), IPv6 link-local addresses (fe80::/10), IPv6 multicast addresses (ff00::/8), and `*.invalid` TLD domains.

#### Scenario: Reject multicast IPv4 address
- **WHEN** user submits `http://224.0.0.1/video`
- **THEN** system MUST raise AppError with code `invalid_url`

#### Scenario: Reject IPv6 private address
- **WHEN** user submits `http://[fc00::1]/video`
- **THEN** system MUST raise AppError with code `invalid_url`

#### Scenario: Reject IPv6 link-local address
- **WHEN** user submits `http://[fe80::1]/video`
- **THEN** system MUST raise AppError with code `invalid_url`

#### Scenario: Reject IPv6 multicast address
- **WHEN** user submits `http://[ff02::1]/video`
- **THEN** system MUST raise AppError with code `invalid_url`

#### Scenario: Reject *.invalid TLD domain
- **WHEN** user submits `http://test.invalid/video`
- **THEN** system MUST raise AppError with code `invalid_url`
