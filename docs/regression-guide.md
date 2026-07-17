# Regression Guide — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Detection

The `RegressionDetector` compares the latest benchmark run against the previous run.

### Thresholds

- Default: 10% decline triggers regression
- Severity:
  - `high`: >25% decline
  - `medium`: 10-25% decline

### Metrics

- `overall` — aggregate score
- Future: per-benchmark metrics

### Reports

Regressions are stored in `automation_regressions` and exposed via:
- CLI: `benchmark automation regressions`
- API: `GET /api/v1/automation/regressions`
