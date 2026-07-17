# Notification Guide — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Supported Channels

- **Console**: Logs to application stdout
- **Webhook**: HTTP POST with JSON payload
- **Slack**: Slack Incoming Webhook
- **Discord**: Discord Webhook
- **Email**: SMTP with SSL

## Events

| Event | Description |
|-------|-------------|
| benchmark.completed | Benchmark finished successfully |
| benchmark.failed | Benchmark execution failed |
| regression.detected | Quality regression detected |
| provider.unavailable | Provider health check failed |
| model.added | New model discovered |
| model.removed | Model removed from provider |

## Configuration

```python
from aibenchmark.app.automation.notifications import (
    NotificationService,
    SlackNotificationProvider,
    EmailNotificationProvider,
)

svc = NotificationService()
svc.register("slack", SlackNotificationProvider("https://hooks.slack.com/services/..."))
svc.register("email", EmailNotificationProvider(
    smtp_host="smtp.example.com",
    smtp_port=465,
    username="alerts@example.com",
    password="secret",
    to_addr="team@example.com",
))
```
