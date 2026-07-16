"""Sprint 11 coverage expansion for analytics.py uncovered paths."""

from __future__ import annotations

from typing import Any

import pytest

from aibenchmark.app.analytics import (
    _category_score,
    _parse_latency,
    _reliability_score,
    best_value,
    build_trends,
    recommend,
    _stability_trend,
)
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score


def _make_result(
    provider: str = "ollama",
    model: str = "llama3",
    benchmark: str = "coding",
    normalized: float = 0.8,
    overall: float | None = None,
    latency_ms: float | None = None,
    details: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
) -> BenchmarkResult:
    return BenchmarkResult(
        provider=ProviderType(provider),
        model=model,
        scores=[Score(benchmark=BenchmarkName(benchmark), raw=normalized, normalized=normalized, weight=1.0)],
        overall=overall if overall is not None else normalized,
        metadata=metadata or {"timestamp": "2026-01-01T00:00:00+00:00", "latency_ms": latency_ms},
        details=details or {},
    )


def test_category_score_finds_category() -> None:
    results = [_make_result(benchmark="coding", normalized=0.9)]
    model, provider, score, latency = _category_score(results, "coding")
    assert model == "llama3"
    assert provider == "ollama"
    assert score == pytest.approx(0.9)


def test_reliability_score_from_benchmark() -> None:
    result = _make_result(benchmark="reliability", normalized=0.95)
    rel = _reliability_score(result)
    assert rel == pytest.approx(0.95)


def test_recommend_alt_reliability_lower_branch() -> None:
    low = _make_result(model="low", benchmark="coding", normalized=0.6, overall=0.6, latency_ms=500.0)
    high = _make_result(model="high", benchmark="coding", normalized=0.9, overall=0.9, latency_ms=100.0)
    recs = recommend([low, high])
    assert recs
    assert recs[0].model == "high"


def test_parse_latency_bad_type_returns_none() -> None:
    result = _make_result(metadata={"latency_ms": object()})
    assert _parse_latency(result) is None


def test_build_trends_single_run_returns_empty() -> None:
    run = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
    trends = build_trends([run])
    assert trends == {}


def test_build_trends_regressed_trend() -> None:
    run1 = _make_result(model="m", provider="ollama", benchmark="coding", overall=0.9, metadata={"timestamp": "2026-01-01T00:00:00+00:00"})
    run2 = _make_result(model="m", provider="ollama", benchmark="coding", overall=0.5, metadata={"timestamp": "2026-01-02T00:00:00+00:00"})
    trends = build_trends([[run1], [run2]])
    key = "ollama:m"
    assert key in trends
    assert trends[key].trend == "regressing"


def test_build_trends_stable_trend() -> None:
    run1 = _make_result(model="m", provider="ollama", benchmark="coding", overall=0.5, metadata={"timestamp": "2026-01-01T00:00:00+00:00"})
    run2 = _make_result(model="m", provider="ollama", benchmark="reasoning", overall=0.5, metadata={"timestamp": "2026-01-02T00:00:00+00:00"})
    trends = build_trends([[run1], [run2]])
    key = "ollama:m"
    assert key in trends
    assert trends[key].trend == "stable"


def test_stability_trend_single_item_returns_none() -> None:
    run = _make_result()
    assert _stability_trend([run]) is None


def test_best_value_empty_candidates_returns_none() -> None:
    assert best_value([]) is None
