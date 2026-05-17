## Why

The GitHub OAuth login redirect currently fails because the GitHub App's callback URL lands on the frontend port 5173 at `/api/auth/github/callback?code=...`, which does not have a mapped route. This leads to a page fallback where the authorization code is lost and login is blocked.

## What Changes

- Map the `/api/auth/github/callback` route in React Router to the `Auth` component.
- Perform a native browser window redirection from `/api/auth/github/callback?code=...` to the backend uvicorn callback endpoint, allowing the browser to follow the OAuth login redirects cleanly and receive the JWT token.

## Capabilities

### New Capabilities
- `github-login-redirect`: Handles incoming browser-native redirects for GitHub OAuth code exchange from any frontend port.

### Modified Capabilities
<!-- No requirement changes to existing core specs -->

## Impact

- `apps/web/src/App.tsx` (Route configuration)
- `apps/web/src/pages/Auth.tsx` (Redirect handling)
