# Confidence Scoring

## Overview

Every recommendation includes a quantitative confidence score backed by
verifiable evidence fields.

## Confidence Formula

```python
def _build_confidence(score, result, category, candidates, by_key):
    base = min(score, 1.0) * 0.7
    score_gap = (candidates[0][0] - candidates[1][0]) * 0.15 if len(candidates) > 1 else 0.0
    reliability = _reliability_score(result) * 0.1 if _reliability_score(result) else 0.0
    history = 0.05 if key in by_key and by_key[key].scores else 0.0
    return min(1.0, max(0.0, base + score_gap + reliability + history))
```

## Confidence Labels

- **High** — confidence >= 0.80
- **Medium** — confidence >= 0.55
- **Low** — confidence < 0.55

## Evidence Fields

Every recommendation carries:

- `confidence` — float [0.0, 1.0]
- `confidence_label` — High / Medium / Low
- `reasons` — list of human-readable evidence strings
- `score` — normalized category score
- `overall` — weighted overall score
- `latency_ms` — measured latency if available
- `reliability` — reliability score if available
- `trade_offs` — top 2 alternatives with scores
- `rejection_reasons` — per-alternative why-they-ranked-lower
- `top_categories` — this model's strongest categories

## Validation

Confidence scores are validated against:
- Score distribution (no >1.0, no <0.0)
- Candidate count (divergence fix for single-candidate lists)
- Sample size (low sample → lower confidence)
- Historical stability coefficient of variation
