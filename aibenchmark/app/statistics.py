from __future__ import annotations

from statistics import mean
from typing import Sequence

from aibenchmark.app.models import BenchmarkResult, StatisticSummary


def summarize(values: Sequence[float]) -> StatisticSummary:
    return StatisticSummary.from_values(list(values))


def category_stats(results: Sequence[BenchmarkResult], category: str) -> StatisticSummary:
    values = []
    for r in results:
        for s in r.scores:
            if s.benchmark.value == category:
                values.append(s.normalized)
    return summarize(values)


def outlier_runs(runs: Sequence[Sequence[BenchmarkResult]], threshold: float = 3.0) -> list[tuple[int, float]]:
    overall_means = []
    for idx, run in enumerate(runs):
        scores = []
        for r in run:
            scores.append(r.overall)
        overall_means.append(mean(scores) if scores else 0.0)
    summary = summarize(overall_means)
    outliers = []
    for idx, val in enumerate(overall_means):
        if summary.std_dev > 0 and abs(val - summary.mean) / summary.std_dev > threshold:
            outliers.append((idx, val))
    return outliers


def score_drift(runs: Sequence[Sequence[BenchmarkResult]]) -> dict[str, float]:
    if len(runs) < 2:
        return {}
    by_model: dict[str, list[BenchmarkResult]] = {}
    for run in runs:
        for r in run:
            key = f"{r.provider.value}:{r.model}"
            by_model.setdefault(key, []).append(r)
    drift: dict[str, float] = {}
    for key, items in by_model.items():
        latest = sorted(items, key=lambda r: r.metadata.get("timestamp", ""))
        if len(latest) < 2:
            continue
        drift[key] = round(latest[-1].overall - latest[-2].overall, 6)
    return drift
