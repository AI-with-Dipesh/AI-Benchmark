# RC Boundary Checklist

This checklist documents the boundary checks applied in the Release Candidate (RC) validation layer, as specified in AD-73.

## Overall Score Bounds

- **Check:** `result.overall` must be in `[0.0, 1.0]`.
- **Severity:** Critical.
- **Rationale:** The benchmark engine normalizes scores to a unit interval; values outside indicate a calculation bug or overflow.

## Raw Score Bounds

- **Check:** Each `score.raw` must be in `[0.0, 1.0]`.
- **Severity:** Major.
- **Rationale:** Raw scores are normalized from provider-specific scales; unclamped values break weighted summation.

## Normalized Score Bounds

- **Check:** Each `score.normalized` must be in `[0.0, 1.0]`.
- **Severity:** Major.
- **Rationale:** Normalized scores are fed to downstream recommendation logic.

## Weight Bounds

- **Check:** Each `score.weight` must be positive (`> 0`).
- **Severity:** Major.
- **Rationale:** Non-positive weights break `calculate_overall()`.

## Metadata Bounds

- **Check:** `retry_count >= 0`
- **Check:** `estimated_cost >= 0` when present
- **Check:** `temperature in [0.0, 2.0]` when present
- **Check:** `top_p in [0.0, 1.0]` when present

## Usage

```python
from aibenchmark.app.rc_validation import validate_rc_bounds

report = validate_rc_bounds(benchmark_result)
if not report.valid:
    raise RuntimeError(report.summary())
```
