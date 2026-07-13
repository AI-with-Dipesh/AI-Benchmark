from __future__ import annotations

import logging
from typing import Sequence

from aibenchmark.app.analytics import recommend
from aibenchmark.app.models import BenchmarkResult, RecommendationStability, ValidationIssue

logger = logging.getLogger(__name__)


def validate_recommendations(runs: Sequence[Sequence[BenchmarkResult]], stability_threshold: float = 0.05) -> RecommendationStability:
    issues: list[ValidationIssue] = []
    if len(runs) < 2:
        issues.append(ValidationIssue("minor", "stability", "Insufficient runs to assess stability"))
        return RecommendationStability(stable=True, flip_count=0, confidence_spread=0.0, issues=issues)

    prev_top = None
    flip_count = 0
    confidence_values: list[float] = []

    for run in runs:
        recs = recommend(run)
        if not recs:
            continue
        top = recs[0].model
        confidence_values.append(recs[0].confidence)
        if prev_top is not None and top != prev_top:
            flip_count += 1
        prev_top = top

    stable = flip_count == 0 and (max(confidence_values) - min(confidence_values)) < stability_threshold if len(confidence_values) > 1 else True
    if not stable:
        issues.append(ValidationIssue("major", "stability", f"Recommendations flipped {flip_count} time(s) across runs"))

    spread = (max(confidence_values) - min(confidence_values)) if confidence_values else 0.0
    return RecommendationStability(stable=stable, flip_count=flip_count, confidence_spread=round(spread, 6), issues=issues)
