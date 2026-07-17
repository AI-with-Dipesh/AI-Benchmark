# Leaderboard

## Overview

Dynamic leaderboard generated from persisted benchmark history.

## Generation

```bash
benchmark leaderboard generate --runs 5 -o outputs/
```

Output: `results.leaderboard` (JSON) with entries:

```json
{
  "rank": 1,
  "model": "tencent/hy3:free",
  "provider": "openrouter",
  "overall": 0.75,
  "category_scores": {
    "coding": 0.75,
    "debugging": 0.12,
    ...
  },
  "latency_ms": 1887.03,
  "recommendation": "Best categories: coding (0.75), research (0.86); latency 1887 ms; Strong overall"
}
```

## Ranking Rules

1. Rank by overall score descending
2. Tie-break by latency ascending
3. Tie-break by model name ascending

## Validation

- Rankings match stored `runs.overall` weighted average
- Category scores match `benchmark_scores.normalized`
- No hardcoded rankings or preferences
