# Database Migration — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## New Tables

| Table | Purpose |
|-------|---------|
| `automation_jobs` | Scheduled job definitions |
| `automation_executions` | Execution history |
| `automation_regressions` | Detected regressions |
| `automation_notifications` | Notification log |
| `automation_sync_history` | Model sync history |

## Migration

The migration is applied automatically on first `AutomationManager` instantiation.

```python
from aibenchmark.app.automation.manager import AutomationManager
manager = AutomationManager()  # auto-migrates
```

## Locations

- Automation DB: `~/.local/share/aibenchmark/automation.db`
- History DB: `~/.local/share/aibenchmark/history.db`
