# Decision Engine

## Overview

The Decision Engine evaluates benchmark history across multiple criteria to
produce actionable engineering recommendations.

Input: `list[BenchmarkResult]` from history or live execution.  
Output: `list[Recommendation]` with confidence, evidence, and trade-offs.

## Evaluation Criteria

- **Benchmark scores** — category-specific normalized scores
- **Historical stability** — variance across repeated runs
- **Failure rate** — success / total attempts
- **Latency** — measured response latency in ms
- **Provider reliability** — health tracker availability
- **Cost** — estimated token cost
- **Context window** — provider-reported capability
- **Tool support** — function calling, structured output flags
- **Benchmark coverage** — number of categories benchmarked

## Implementation

Module: `aibenchmark/app/analytics.py`  
Functions:
- `recommend()` — best model per category
- `build_team()` — AI engineering team roles
- `best_value()` — best score-per-ms ratio
- `fastest()` — lowest latency model
- `highest_quality()` — highest overall score model

All decisions are computed dynamically at runtime from stored evidence.

## Routing Integration

The Decision Engine feeds directly into `engine.select_model()` via
`RoutingContext`, which applies cost-aware, capability-first, health-first,
or round-robin strategies.

## Confidence Calculation

Every confidence score is computed, not hardcoded.  
Formula: `min(1.0, max(0.0, base + score_gap + reliability + history))`

Where:
- base = score * 0.7
- score_gap = (top_score - second_score) * 0.15
- reliability = reliability_score * 0.1
- history = 0.05 if historical run exists
