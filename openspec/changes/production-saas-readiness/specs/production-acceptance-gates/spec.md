## ADDED Requirements

### Requirement: Production API acceptance
The system SHALL define API acceptance gates for beta release.

#### Scenario: API release gate
- **WHEN** the beta release is evaluated
- **THEN** registration control, login, current-user, quota enforcement, task ownership, and administrator controls are verified

### Requirement: Production frontend acceptance
The system SHALL define frontend acceptance gates for beta release.

#### Scenario: Frontend release gate
- **WHEN** the beta release is evaluated in a browser
- **THEN** login, registration control messaging, download workspace, task list, task detail, quota display, and error states are verified

### Requirement: Production download acceptance
The system SHALL define download acceptance gates for beta release.

#### Scenario: Download release gate
- **WHEN** the beta release is evaluated
- **THEN** at least three legal public parse samples and one small full download sample are verified with documented evidence

### Requirement: Compliance negative acceptance
The system SHALL define negative acceptance gates for prohibited capabilities.

#### Scenario: Prohibited capability rejected
- **WHEN** DRM, paywall, member-only, private-link, Cookie-hosting, or platform-bypass scenarios are evaluated
- **THEN** the system does not provide bypass capability and records the expected rejection or unsupported result
