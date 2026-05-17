# Specification: GitHub Login Redirect

This specification outlines the behavior and scenarios for the new browser-native GitHub OAuth login redirect handling.

## ADDED Requirements

### Requirement: REQ-001 - Mapped Frontend Callback Route
The frontend application MUST map the incoming callback route `/api/auth/github/callback` to the Auth page component to capture authorization redirect parameters.

#### Scenario: Navigate to callback route with code
- **Given** the frontend server is running on `http://localhost:5173`
- **When** a user visits `http://localhost:5173/api/auth/github/callback?code=test_code`
- **Then** the Auth component should be mounted and loaded.

### Requirement: REQ-002 - Native Browser Window Redirect
When the Auth component is mounted and detects a `code` query parameter in the search string, it MUST immediately redirect the native `window.location.href` to the backend uvicorn callback endpoint at `${siteConfig.apiBaseUrl}/auth/github/callback?code=${code}` to trigger secure token exchange and subsequent redirection.

#### Scenario: Forward to backend callback
- **Given** the Auth page mounts with a `code` query parameter
- **When** `code` is detected
- **Then** the page sets `window.location.href` to redirect to the backend API callback endpoint.
