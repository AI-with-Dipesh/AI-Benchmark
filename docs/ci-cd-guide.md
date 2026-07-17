# CI/CD Integration Guide — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## API-Based Integration

### Trigger Benchmark

```bash
curl -X POST http://benchmark.example.com/api/v1/automation/jobs/1/run
```

### Check History

```bash
curl http://benchmark.example.com/api/v1/automation/history
```

### Get Regressions

```bash
curl http://benchmark.example.com/api/v1/automation/regressions
```

### GitHub Actions

```yaml
name: Benchmark
on: [push, schedule]
jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - name: Trigger benchmark
        run: curl -X POST $BENCHMARK_URL/api/v1/automation/jobs/1/run
      - name: Wait and collect
        run: sleep 60 && curl $BENCHMARK_URL/api/v1/automation/history
```

### GitLab CI

```yaml
benchmark:
  script:
    - curl -X POST $BENCHMARK_URL/api/v1/automation/jobs/1/run
    - sleep 60
    - curl $BENCHMARK_URL/api/v1/automation/history
```
