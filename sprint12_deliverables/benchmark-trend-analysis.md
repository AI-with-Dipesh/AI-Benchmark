# Benchmark Trend Analysis

## Overview

Historical trend analysis tracks model quality, ranking stability, provider
comparison, and regression detection across benchmark runs.

## Implementation

Module: `aibenchmark/app/analytics.py`  
Functions:
- `build_trends(runs)` — per-model category deltas and overall trend
- `build_comparison(run_a, run_b)` — category-level improvement/regression
- `_stability_trend(items)` — mean absolute delta between consecutive runs
- `most_stable(runs)` — most stable model across runs

## Trend Types

- `improving` — overall delta > 0.01
- `regressing` — overall delta < -0.01
- `stable` — delta within noise bounds

## Statistics Computed

Per model:
- Average
- Median
- Variance
- Standard deviation
- Confidence interval (95%)
- Coefficient of variation
- Ranking movement
- Latency delta
- Stability delta

## CLI

```bash
benchmark trends --runs 5
benchmark compare --against-runs 2
```

## Regression Detection

- Delta > 0.01 = improved
- Delta < -0.01 = regressed
- Absent or flat = stable/new/removed

## Persistence

Trends are computed from `history.load_latest(N)` and do not require
additional storage beyond existing run records.
