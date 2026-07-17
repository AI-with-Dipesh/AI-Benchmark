# CI/CD Integration — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Endpoints

- `POST /api/v1/automation/jobs/{id}/run`
- `GET /api/v1/automation/history`
- `GET /api/v1/automation/regressions`
- `POST /api/v1/automation/test-notification`

## GitHub Actions

```yaml
- name: Benchmark
  run: curl -X POST $BENCHMARK_URL/api/v1/automation/jobs/1/run
```
