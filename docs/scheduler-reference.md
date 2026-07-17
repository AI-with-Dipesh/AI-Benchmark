# Scheduler Reference — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Job Model

| Field | Type | Description |
|-------|------|-------------|
| job_id | int | Primary key |
| name | str | Human-readable name |
| schedule_cron | str | Cron expression |
| provider_name | str | Target provider |
| model_filter | str | Optional model filter |
| benchmarks | str | Comma-separated benchmark names |
| enabled | bool | Enable/disable job |
| concurrency | int | Parallel workers |
| timeout_seconds | float | Job timeout |
| retry_count | int | Max retries |

## Cron Expressions

| Expression | Meaning |
|-----------|---------|
| `0 * * * *` | Hourly |
| `0 0 * * *` | Daily |
| `0 0 * * 0` | Weekly |
| `0 0 1 * *` | Monthly |

## Execution States

| Status | Meaning |
|--------|---------|
| pending | Queued |
| running | In progress |
| success | Completed |
| failed | Error occurred |
| cancelled | User cancelled |

## Triggers

| Trigger | Description |
|---------|-------------|
| scheduled | Cron trigger |
| manual | CLI/API trigger |
| retry | Auto-retry |
| webhook | HTTP trigger |
