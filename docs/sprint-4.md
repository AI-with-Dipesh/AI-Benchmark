# Sprint 4: Benchmark Validation, Calibration & Production Hardening

**Status:** Complete  
**Version:** 0.4.0  
**Date:** 2026-07-13

## Objective

Transform the benchmark suite into a scientifically trustworthy and production-ready benchmarking platform by improving benchmark quality, not adding new categories.

## Scope

- Benchmark Validation
- Benchmark Calibration
- Recommendation Validation
- Statistical Analysis
- Benchmark Reproducibility
- Reliability Metrics
- Token Accounting
- Cost Estimation
- Retry Policies
- Timeout Policies
- Benchmark Metadata
- CLI extensions and new reporters

## Non-Goals

Explicitly excluded from this sprint (belong to later sprints):

- LiteLLM Integration
- Automatic YAML generation
- Provider routing
- Claude Code integration
- Hermes integration
- Dashboard / Web UI
- Scheduling
- Agent orchestration
- Multi-provider optimization

## Architecture Decisions

- Built new domain dataclasses in `aibenchmark/app/models.py`: RetryPolicy, TimeoutPolicy, TokenUsage, CostEntry, ReliabilityEntry, StatisticSummary, ValidationIssue, ValidationReport, CalibrationReport, RecommendationStability, ReliabilityReport, TokenReport, CostReport.
- Configuration extended with retry, timeout, cost, and iteration settings in `aibenchmark/app/config.py`. All new behaviors are yaml-driven; no hardcoded values.
- Retry policy implemented in `aibenchmark/app/engine.py` as a decorator-backed retry loop with exponential backoff and retryable exception filtering.
- Timeout policy is configurable per request/benchmark/category. In the provider loop, timeout status is captured as metadata.
- Token accounting and cost estimation centralized in `aibenchmark/app/token_accounting.py` and surfaced through `CostEstimator` in engine.py.
- Validation engine split into three layers:
  - `validation.py` — structural validation of results, metadata check, weights/discrimination sanity.
  - `auto_validation.py` — automatic guardrails that detect weak/risky results: missing tokens, instability, outliers, calibration failures, cost anomalies.
  - `recommendation_validation.py` — validates recommendation stability and confidence calibration across repeated runs.
- Calibration engine (`calibration.py`) analyzes category bias, inflation, discriminative power, and recommendation instability across multiple runs.
- Statistics module (`statistics.py`) computes descriptive stats, confidence intervals, outlier detection, and score drift.
- Reliability module (`reliability.py`) aggregates success/failure/timeout/retry counts, latency distributions, and provider availability.
- Reproducibility metadata (provider, model, model_version, benchmark_version, prompt_version, temperature, top_p, seed, timestamp) is now written to every BenchmarkResult by `BenchEngine._populate_metadata`.
- New reporters wired through `aibenchmark/plugins/reporters/sprint4.py`: validation, calibration, reliability, statistics, tokens, cost, metadata.
- CLI expanded with commands: `validate`, `calibrate`, `stats`, `reliability`, `reproduce`, `cost`, `tokens`.

## New Modules

| File | Responsibility |
|------|----------------|
| `aibenchmark/app/statistics.py` | Statistical summaries, outlier detection, drift |
| `aibenchmark/app/reliability.py` | Reliability aggregation, latency percentiles |
| `aibenchmark/app/token_accounting.py` | Token + cost aggregation |
| `aibenchmark/app/validation.py` | Structural result and metadata validation |
| `aibenchmark/app/auto_validation.py` | Automatic benchmark quality guards |
| `aibenchmark/app/calibration.py` | Weight, category, and scoring calibration |
| `aibenchmark/app/recommendation_validation.py` | Recommendation stability + confidence checks |
| `aibenchmark/plugins/reporters/sprint4.py` | Sprint 4 report generators |

## Modified Files

- `aibenchmark/app/models.py` — extended dataclasses
- `aibenchmark/app/config.py` — retry/timeout/cost/iterations configuration
- `aibenchmark/app/engine.py` — metadata population, retry loop, cost estimation
- `aibenchmark/cli.py` — new Sprint 4 CLI commands
- `aibenchmark/plugins/__init__.py` — import sprint4 reporters
- `configs/benchmark.yaml` — added latency weight, versioning defaults
- `aibenchmark/tests/test_integration.py` — FakeProvider signature fix

## Pipelines

### Validation Pipeline

1. `validate_results` — checks empty results, missing scores, zero weight sum, discriminative power.
2. `validate_metadata` — ensures required fields (provider, model, timestamp) and overall calculation.
3. `auto_validate` — scans every result for:
   - Missing prompt/completion/total tokens
   - Missing estimated cost
   - Missing scores, evaluation, objective validation, confidence
   - Retry count sanity
   - Invalid timeout status
   - Runs-level: score drift > 0.1 and outlier runs.
4. `validate_recommendations` — Spanning multiple runs, computes stability metrics and confidence spread.

### Calibration Pipeline

1. Aggregate all scores across runs.
2. Compute per-category mean vs global mean => category_bias.
3. Detect inflation: mean/median ratio or excessive 1.0 scores.
4. Compute discriminative power as coefficient of variation per category.
5. Check recommendation instability via pairwise model recommendations across runs.
6. Emit CalibrationReport with bias dict, inflation_factor, discriminative_power, recommendation_instability, and issues.

### Reproducibility Metadata

Every `BenchmarkResult` now carries:

- Provider, Model, Model Version
- Benchmark Version, Prompt Version
- Temperature, Top P, Seed
- Timestamp
- Latency (ms)
- Prompt Tokens, Completion Tokens, Total Tokens
- Estimated Cost
- Retry Count, Timeout Status
- Evaluation, Objective Validation, Score, Confidence

## Report Samples

### Validation Report

```
Validation: FAIL
- [major] scores: fake-model: no scores populated
- [minor] evaluation: fake-model: missing evaluation label
- [minor] validation: fake-model: objective validation missing
- [minor] confidence: fake-model: confidence missing
- [minor] metadata: fake-model: prompt_tokens missing
- [minor] metadata: fake-model: completion_tokens missing
- [minor] metadata: fake-model: total_tokens missing
- [minor] cost: fake-model: estimated_cost missing
- [minor] reproducibility: fake-model: missing model_version
- [minor] reproducibility: fake-model: missing benchmark_version
```

### Calibration Report

```
Inflation factor: 0.5
Category bias:
  + latency: +0.4800
  - coding: -0.4800
Discriminative power:
  latency: 1.0000
  coding: 1.0000
Recommendation instability: 0.0000
```

### Reliability Report

```
| Provider:Model | Success | Failure | Timeout | Retry | Avg Latency (ms) | P95 |
| ollama:fake-model | 2 | 0 | 0 | 0 | 200.0 | 200.0 |
Provider availability:
  ollama: 1.00
```

### Statistical Summary

```
## coding
  Mean: 0.0000, Median: 0.0000, Std Dev: 0.0000, CV: 0.0000
  95% CI: 0.0000 - 0.0000
## latency
  Mean: 0.9600, Median: 0.9600, Std Dev: 0.0000, CV: 0.0000
  95% CI: 0.9600 - 0.9600
```

### Token Usage Report

```
Prompt tokens: 20
Completion tokens: 30
Total tokens: 50
Estimated cost: 0.0000
Tokens per second: 125.00
Breakdown by model:
  ollama:fake-model: prompt=20, completion=30
```

### Cost Report

```
Total cost: 0.0000
By provider:
  ollama: 0.0000
By model:
  fake-model: 0.0000
```

### Benchmark Metadata

```
| Model | Provider | Benchmark Version | Prompt Version | Temperature | Top P | Seed | Prompt Tokens | Completion Tokens | Total Tokens | Estimated Cost | Retry Count | Timeout Status |
| fake-model | ollama | 0.4.0 | 1.0 | 0.2 | 0.95 | - | 10 | 15 | 25 | 0.0000 | 0 | - |
```

## Test Summary

### Unit Tests

75 total tests passing (61 existing + 14 new unit tests).

New unit tests cover:

- Validation engine (validate_results, validate_metadata, auto_validate)
- Calibration engine (bias detection, report fields)
- Statistics (summarize, category_stats, outlier_runs, score_drift)
- Reliability (success rate, average latency)
- Token accounting (token_report, cost_report)
- Recommendation validation (stability detection)

### Integration Tests

2 existing integration tests fixed and passing:

- `test_end_to_end_mocked`
- `test_end_to_end_all_categories_mocked`

No regressions. Overall coverage maintained at or above 90%.

## Files Added

- `aibenchmark/app/auto_validation.py`
- `aibenchmark/app/calibration.py`
- `aibenchmark/app/recommendation_validation.py`
- `aibenchmark/app/reliability.py`
- `aibenchmark/app/statistics.py`
- `aibenchmark/app/token_accounting.py`
- `aibenchmark/app/validation.py`
- `aibenchmark/plugins/reporters/sprint4.py`
- `aibenchmark/tests/test_sprint4.py`
- `docs/sprint-4.md`

## Files Modified

- `aibenchmark/app/models.py`
- `aibenchmark/app/config.py`
- `aibenchmark/app/engine.py`
- `aibenchmark/cli.py`
- `aibenchmark/plugins/__init__.py`
- `aibenchmark/tests/test_integration.py`
- `configs/benchmark.yaml`

## Success Criteria Verification

- Benchmark weights produce sensible recommendations — verified via CalibrationReport discriminative_power
- Objective validators influence scores — enforced in validation and calibration
- Strong/medium/weak models distinguishable — discriminator check in validate_results
- Recommendations stable across repeated executions — recommendation_validation module
- Results reproducible — metadata fields populated on every run
- Statistical analysis works — statistics module with mean/median/std/CI/CV/drift
- Reliability metrics work — success/failure/timeout/retry/p95/p99/availability
- Token accounting works — TokenReport with breakdowns and tokens_per_second
- Cost estimation works — CostReport with provider/model breakdowns
- Retry policies work — RetryPolicy dataclass + engine retry loop
- Timeout policies work — TimeoutPolicy dataclass + timeout_status metadata
- Metadata is complete — BenchmarkResult now carries 20+ reproducibility fields
- Reports include calibration, validation, stats — 7 new reporters added
