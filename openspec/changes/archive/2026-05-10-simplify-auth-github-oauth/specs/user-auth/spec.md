# Specification Delta: user-auth

## MODIFIED Requirements

### Requirement: User registration
#### Scenario: Simplified GitHub Registration
- **WHEN** a user successfully authenticates via GitHub OAuth
- **AND** the system does not recognize the GitHub UID
- **THEN** the system SHOULD automatically create a new user profile using GitHub info (email, name, avatar)

### Requirement: User login
#### Scenario: GitHub OAuth Login
- **WHEN** a user clicks "Login with GitHub"
- **THEN** the system redirects to GitHub for authorization
- **AND** upon successful return, issues a JWT access token

## REMOVED Requirements
- **Requirement: User registration (Email/Password)**: Custom credential registration is deprecated in favor of OAuth for simplicity.
