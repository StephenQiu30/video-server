## 1. Database & Model Updates

- [x] 1.1 Add `github_id` and `avatar_url` fields to `User` model in `app/models.py`.
- [x] 1.2 Make `password_hash` nullable in `app/models.py`.
- [x] 1.3 Create and apply database migration for user model changes.

## 2. Backend GitHub OAuth Integration

- [x] 2.1 Update `get_settings` in `app/core/config.py` to include GitHub OAuth credentials.
- [x] 2.2 Implement GitHub OAuth callback handler in `app/routers/auth.py`.
- [x] 2.3 Implement quiet registration logic (create user if not exists) during callback.
- [x] 2.4 Update login logic to issue JWT based on GitHub authentication.

## 3. Frontend Auth UI Simplification

- [x] 3.1 Simplify `Auth.tsx` by removing complex registration/login forms.
- [x] 3.2 Add "Login with GitHub" button and implement redirect to GitHub auth URL.
- [x] 3.3 Add a simple "Welcome" or "Authenticated" state feedback.

## 4. Testing & Cleanup

- [x] 4.1 Write integration tests for the GitHub OAuth callback (mocking GitHub API).
- [x] 4.2 Remove/Deprecate legacy password-based routes if safe.
- [x] 4.3 Verify end-to-end login flow.
- [x] 4.4 Archive the change and sync specs.
