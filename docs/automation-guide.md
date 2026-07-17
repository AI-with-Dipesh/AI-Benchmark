# Automation Guide — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Overview

Sprint 15 adds production-grade automation to AI-Benchmark. The platform can now run scheduled benchmarks, sync models, detect regressions, and send notifications.

## Automation Manager

The `AutomationManager` provides persistent job storage, execution history, regression tracking, and notification logging.

### Creating a Job

CLI:
```bash
python -m aibenchmark.cli automation create \
  --name "daily-bench" \
  --schedule "0 0 * * *" \
  --provider openrouter \
  --benchmarks "coding,latency" \
  --concurrency 2
```

API:
```bash
curl -X POST http://localhost:8000/api/v1/automation/jobs \
  -H "Content-Type: application/json" \
  -d '{"name":"daily-bench","schedule_cron":"0 0 * * *","provider_name":"openrouter","benchmarks":"coding,latency"}'
```

### Running a Job

CLI:
```bash
python -m aibenchmark.cli automation run 1
```

API:
```bash
curl -X POST http://localhost:8000/api/v1/automation/jobs/1/run
```

## Model Synchronization

Model sync runs automatically when `list_models()` is called. History is tracked in `automation_sync_history`.

## Regression Detection

Compares new benchmark runs against the previous run. Detects:
- Performance drops (>10% decline)
- Cost increases
- Availability issues

## Notifications

Supported channels:
- `console` — logs to stdout
- `webhook` — HTTP POST
- `slack` — Slack webhook
- `discord` — Discord webhook
- `email` — SMTP

Configure via code:
```python
from aibenchmark.app.automation.notifications import NotificationService, ConsoleNotificationProvider
svc = NotificationService()
svc.register("console", ConsoleNotificationProvider())
svc.send("console", "Benchmark Complete", "All tests passed", execution_id=1)
```

## CI/CD Integration

Use the API endpoints to trigger benchmarks from GitHub Actions, GitLab CI, Jenkins, or Azure DevOps.

GitHub Actions example:
```yaml
- name: Run benchmark
  run: |
    curl -X POST http://benchmark.example.com/api/v1/automation/jobs/1/run
    curl http://benchmark.example.com/api/v1/automation/history
```
