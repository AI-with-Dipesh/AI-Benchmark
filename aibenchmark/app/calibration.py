from __future__ import annotations

import logging
from collections import defaultdict
from typing import Sequence

from aibenchmark.app.models import BenchmarkResult, CalibrationReport, ValidationIssue

logger = logging.getLogger(__name__)


def calibrate(results: Sequence[Sequence[BenchmarkResult]]) -> CalibrationReport:
    issues: list[ValidationIssue] = []
    flat: list[BenchmarkResult] = []
    for run in results:
        flat.extend(run)

    # category bias: mean per category vs overall mean
    cat_scores: dict[str, list[float]] = defaultdict(list)
    for r in flat:
        for s in r.scores:
            cat_scores[s.benchmark.value].append(s.normalized)

    overall_mean = _overall_mean(flat)
    category_bias: dict[str, float] = {}
    for cat, vals in cat_scores.items():
        mean_val = sum(vals) / len(vals) if vals else 0.0
        category_bias[cat] = round(mean_val - overall_mean, 6)
        if abs(category_bias[cat]) > 0.15:
            issues.append(ValidationIssue("major", "bias", f"Category '{cat}' is biased by {category_bias[cat]:+.2f}"))

    # inflation factor
    inflated = sum(1 for r in flat for s in r.scores if s.normalized > 0.95)
    inflation_factor = (inflated / sum(len(r.scores) for r in flat)) if flat else 0.0

    # discriminative power by category
    discriminative_power: dict[str, float] = {}
    for cat, vals in cat_scores.items():
        uniq = len(set(round(v, 4) for v in vals))
        discriminative_power[cat] = min(1.0, uniq / max(1, len(vals)))
        if discriminative_power[cat] < 0.5:
            issues.append(ValidationIssue("major", "discriminative_power", f"Category '{cat}' has poor discriminative power {discriminative_power[cat]:.2f}"))

    # recommendation instability: use variance of top scores per category across runs
    recommendation_instability = _instability(results)

    return CalibrationReport(
        category_bias=category_bias,
        inflation_factor=round(inflation_factor, 6),
        discriminative_power=discriminative_power,
        recommendation_instability=round(recommendation_instability, 6),
        issues=issues,
    )


def _overall_mean(results: Sequence[BenchmarkResult]) -> float:
    vals = [r.overall for r in results if r.scores]
    return sum(vals) / len(vals) if vals else 0.0


def _instability(runs: Sequence[Sequence[BenchmarkResult]]) -> float:
    if len(runs) < 2:
        return 0.0
    top_models: list[str | None] = []
    for run in runs:
        if not run:
            top_models.append(None)
            continue
        best = max(run, key=lambda r: r.overall)
        top_models.append(best.model)
    flips = sum(1 for i in range(1, len(top_models)) if top_models[i] != top_models[i - 1])
    return flips / max(1, len(top_models) - 1)
