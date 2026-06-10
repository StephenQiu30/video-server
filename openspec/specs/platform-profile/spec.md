# Platform Profile

## Purpose

Define the accepted platform profile contract for the video-server project, including platform identification fields, compliance note requirements, and API response format.

## Requirements

### Requirement: Platform Profile Registry Must Exist

The system MUST maintain a registry of formally supported platform profiles.

#### Scenario: Supported platforms are registered

- **GIVEN** the video-server system is running
- **WHEN** a contributor inspects the platform profile registry
- **THEN** the registry contains profiles for YouTube, Bilibili, TikTok, X, and Instagram
- **AND** each profile includes `platform_id`, `display_name`, `category`, and `compliance_note`

### Requirement: Platform Identification Must Return Unified Fields

The API MUST return unified platform fields when a task is created or queried.

#### Scenario: Task creation returns platform fields

- **GIVEN** a user submits a valid public video URL
- **WHEN** the system creates a task
- **THEN** the API response includes `platform_id`, `platform_display_name`, `platform_category`, and `platform_compliance_note`
- **AND** the values match the registered platform profile

#### Scenario: Task detail returns platform fields

- **GIVEN** a task has been created with a valid URL
- **WHEN** the user queries the task detail
- **THEN** the response includes `platform_id`, `platform_display_name`, `platform_category`, and `platform_compliance_note`

### Requirement: Compliance Notes Must Not Promise Bypass Capabilities

The system MUST NOT include language in compliance notes that promises or implies the ability to bypass platform restrictions.

#### Scenario: Compliance note does not promise login bypass

- **GIVEN** a platform profile has a `compliance_note`
- **WHEN** the compliance note is reviewed
- **THEN** the note does not promise bypassing login, CAPTCHA, age verification, membership, or private access restrictions

#### Scenario: Unsupported platform shows best-effort notice

- **GIVEN** a URL from an unrecognized platform
- **WHEN** the system processes the URL
- **THEN** the system returns a best-effort notice
- **AND** the notice does not make formal support promises

### Requirement: Platform Profile Fields Must Be Stable

The platform profile contract MUST remain stable across API versions.

#### Scenario: Field names are consistent

- **GIVEN** the platform profile contract is defined
- **WHEN** the API returns platform fields
- **THEN** the field names are `platform_id`, `platform_display_name`, `platform_category`, and `platform_compliance_note`
- **AND** the field names do not change without a documented contract update

## Validation

- `npm test` must pass with platform profile tests
- Platform profile registry contains all 5 formally supported platforms
- API responses include all required platform fields
- Compliance notes do not contain bypass-promising language
