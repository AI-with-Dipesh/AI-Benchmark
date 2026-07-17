# Recommendation Engine

## Overview

The Recommendation Engine consumes benchmark history and produces dynamic,
evidence-backed engineering recommendations for every task category.

No recommendation is static. Every recommendation is derived from live
benchmark evidence via `analytics.recommend()`.

## Supported Categories

- Coding
- Debugging
- Architecture
- Documentation
- Research
- Security
- Testing
- Code Review
- JSON Generation
- Long Context
- Reasoning
- Instruction Following
- General Chat

## Implementation

Module: `aibenchmark/app/analytics.py`  
Function: `recommend(results: Sequence[BenchmarkResult]) -> list[Recommendation]`

### Algorithm

1. Group benchmark results by `provider:model`, retaining the highest overall.
2. For each benchmark category present in results:
   a. Identify the best normalized score.
   b. Check latency (prefer < 200 ms).
   c. Check reliability (prefer > 0.9).
   d. Check all-round performance (overall >= 0.85).
   e. Build candidate list with trade-offs.
3. Compute confidence score with evidence quality weighting.
4. Build rejection reasons for lower-ranked alternatives.

## Data Model

```python
@dataclass(frozen=True)
class Recommendation:
    category: str
    model: str
    provider: str
    confidence: float
    confidence_label: str
    reasons: list[str]
    score: float = 0.0
    latency_ms: float | None = None
    reliability: float | None = None
    trade_offs: list[str] = field(default_factory=list)
    overall: float = 0.0
    category_weight: float = 1.0
    rejection_reasons: dict[str, list[str]] = field(default_factory=dict)
    top_categories: list[tuple[str, float]] = field(default_factory=list)
```

## Validation

- 500 unit tests pass
- 95.11% coverage
- End-to-end CLI command `benchmark recommend --runs 1` executes successfully
- Output written to `results.recommendations`
