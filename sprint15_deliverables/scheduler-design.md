# Scheduler Design — Sprint 15

**Sprint**: 15
**Release**: v2.2.0
**Date**: 2026-07-17

## BenchmarkScheduler

The scheduler executes `AutomationJob` instances against the `BenchEngine`.

### Job Lifecycle

1. Job created via CLI/API
2. `BenchmarkScheduler.run_job(job)` called
3. `AutomationExecution` record created
4. Engine executes benchmarks
5. Results saved to history
6. Regression detection runs
7. Notifications sent

### Concurrency

- Per-job `concurrency` setting
- Respects provider rate limits
- Thread-safe singleton engines
