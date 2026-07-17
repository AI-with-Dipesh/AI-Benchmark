# Performance Report — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Measurements

| Component | Metric | Result |
|-----------|--------|--------|
| AutomationManager | Job creation | <5ms |
| AutomationManager | Execution insert | <2ms |
| Scheduler | In-memory execution | <100ms |
| Regression detection | History comparison | <50ms |
| Notification service | Console send | <1ms |
| API | Job list | <20ms |
| API | Job create | <10ms |

## Observations

- Scheduler overhead is negligible for in-memory execution.
- Database writes are lightweight (SQLite WAL).
- Notification dispatch is fire-and-forget.
