# Regression Engine — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## Detection Logic

1. Load last 2 benchmark runs
2. Align results by model name
3. Compare `overall` and per-benchmark scores
4. Flag declines > threshold (default 10%)

### Severity

- **high**: >25% decline
- **medium**: 10-25% decline

### Persistence

Regressions stored in `automation_regressions` table.
