# BENCHMARK BUG REPORT — Sprint 11.5

**Generated**: 2026-07-17 06:00:00 UTC
**Assessor**: Implementation Authority
**Project**: AI-Benchmark v1.3.0
**Sprint**: 11.5 — Benchmark Engine Validation & Calibration

---

## Executive Summary

Two confirmed defects were identified and fixed in the benchmark scoring pipeline.
Both defects caused incorrect benchmark scores, leaderboard rankings, reports,
and recommendations.

---

## Confirmed Defects

### BUG-001: Engine Score Reconstruction Loses Normalization

| Attribute | Value |
|-----------|-------|
| **Severity** | HIGH |
| **Component** | `aibenchmark/app/engine.py` — `_execute_single_benchmark` |
| **Impact** | All non-latency benchmark categories stored `normalized=0.0` and `weighted=0.0`, causing `runs.overall=0.0` for every run |
| **Likelihood** | 100% — affects every benchmark execution |
| **Regression risk** | LOW — fix preserves backward-compatible reconstruction path |

**Root Cause:**

The engine ignored the `Score` objects already computed by benchmark plugins
and reconstructed new `Score` instances from `result.details`:

```python
score = Score(
    benchmark=benchmark_name_enum,
    raw=result.details.get("raw_score", 0.0),
    normalized=result.details.get("normalized", 0.0),
    weight=weight,
)
result.scores = [score]
```

However, benchmark plugins store `details` as:
```python
details={"raw_score": result.raw.get("score", result.score), **result.metadata}
```

The `normalized` value computed by evaluators is **not** stored in `details`
(except for the latency benchmark, which explicitly includes it).
Consequently, `result.details.get("normalized", 0.0)` returned `0.0` for all
non-latency benchmarks.

**Affected Subsystems:**

- `benchmark_scores.normalized` — stored as 0.0
- `benchmark_scores.weighted` — stored as 0.0  
- `runs.overall` — stored as 0.0
- Leaderboard queries — sorted by zero values
- Analytics/recommendations — all decisions based on zero scores
- Report generation — displayed 0.00 scores
- Confidence calculations — derived from 0.0 normalized values

**Fix:**

In `engine.py`, use the existing `Score` from `result.scores[0]` when present.
Only fall back to reconstruction when scores list is empty.

```python
if result.scores:
    score = result.scores[0]
    score.weight = weight
    score.weighted = score.normalized * weight
    result.scores = [score]
else:
    score = Score(
        benchmark=benchmark_name_enum,
        raw=result.details.get("raw_score", 0.0),
        normalized=result.details.get("normalized", 0.0),
        weight=weight,
    )
    result.scores = [score]
```

**Verification:**

Before fix: `coding: 0.00 [success]`
After fix: `coding: 0.75 [success]` (tencent/hy3:free)

---

### BUG-002: Aggregate Run Overall Not Calculated

| Attribute | Value |
|-----------|-------|
| **Severity** | MEDIUM |
| **Component** | `aibenchmark/app/history.py` — `save_run` |
| **Impact** | `runs.overall` stored only the first benchmark's score, not the weighted average across all categories |
| **Likelihood** | 100% for multi-benchmark runs |
| **Regression risk** | LOW |

**Root Cause:**

`save_run` used `primary.overall` where `primary = results[0]`. Since each
`run_benchmark` call returns a single-category `BenchmarkResult`, the stored
`runs.overall` reflected only the first category (e.g., coding) rather than
the aggregate weighted average across all categories.

**Affected Subsystems:**

- `runs.overall` in history DB
- Leaderboard ranking (when sorting by `runs.overall`)
- Cross-run comparisons

**Fix:**

Compute aggregate overall in `save_run`:

```python
total_weight = sum(s.weight for r in results for s in r.scores)
weighted_sum = sum(s.weighted for r in results for s in r.scores)
aggregate_overall = weighted_sum / total_weight if total_weight else 0.0
# store aggregate_overall instead of primary.overall
```

---

### BUG-003: validate_metadata False Positive on Zero Overall

| Attribute | Value |
|-----------|-------|
| **Severity** | LOW |
| **Component** | `aibenchmark/app/validation.py` — `validate_metadata` |
| **Impact** | Valid zero scores incorrectly flagged as "Overall score not calculated" |
| **Likelihood** | Low in practice; triggered only by zero-score models |
| **Regression risk** | NONE |

**Root Cause:**

`if result.scores and not result.overall:` evaluated `not 0.0` as `True`.

**Fix:**

Changed to `if result.scores and result.overall is None:`

---

## Additional Investigation Findings

No additional bugs were discovered in:
- Evaluator normalization logic (`_normalize` is correct)
- Score weighted calculation (`Score.__post_init__` is correct)
- BenchmarkResult.calculate_overall() (correct formula)
- Provider result parsing
- Model metadata handling
- Retry/backoff logic
- Rate limit tracking
- Failure recovery / fallback
- JSON/CSV serialization
- History load_run reconstruction
- Percentile calculations
- Reporter plugins (read-only consumers; correct once source data is fixed)

---

## Files Modified

| File | Change |
|------|--------|
| `aibenchmark/app/engine.py` | Preserve benchmark-computed Score normalized values |
| `aibenchmark/app/history.py` | Compute aggregate overall across all category scores |
| `aibenchmark/app/validation.py` | Fixed false positive on zero overall |
| `aibenchmark/tests/test_sprint11_coverage_engine.py` | Added 4 regression tests |

---

## Tests Added

1. `test_engine_preserves_benchmark_computed_normalized` — verifies Score.normalized survives engine processing
2. `test_engine_recalculates_overall_from_preserved_scores` — verifies overall = weighted avg of preserved scores
3. `test_engine_fallback_reconstruction_when_scores_empty` — verifies fallback path still works
4. `test_validate_metadata_zero_overall_not_flagged` — verifies zero overall is valid
