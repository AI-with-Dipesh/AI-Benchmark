# Release Notes — v2.2.0

**Release Date**: 2026-07-17
**Type**: Minor

## Highlights

- Added automation framework with job scheduling
- Model synchronization service
- Quality regression detection
- Notification system (console, webhook, Slack, Discord, email)
- CI/CD integration endpoints

## New CLI Commands

- `benchmark automation create`
- `benchmark automation list`
- `benchmark automation run`
- `benchmark automation delete`
- `benchmark automation history`
- `benchmark automation regressions`
- `benchmark automation notifications`

## New API Endpoints

- `GET /api/v1/automation/jobs`
- `POST /api/v1/automation/jobs`
- `PATCH /api/v1/automation/jobs/{id}`
- `DELETE /api/v1/automation/jobs/{id}`
- `POST /api/v1/automation/jobs/{id}/run`
- `GET /api/v1/automation/history`
- `GET /api/v1/automation/regressions`
- `GET /api/v1/automation/notifications`
- `POST /api/v1/automation/test-notification`

## Breaking Changes

None.

## Upgrade Notes

No migration steps required. Automation database created on first use.
