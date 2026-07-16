from __future__ import annotations

from unittest.mock import patch


from aibenchmark.app.auto_validation import auto_validate
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score


def _make_result(model: str = "m1", provider: str = "openrouter", scores=None, metadata=None, **kwargs):
    if scores is None:
        scores = [Score(benchmark=BenchmarkName.GENERAL, raw=0.5, normalized=0.5, weight=1.0, weighted=0.5)]
    return BenchmarkResult(
        model=model,
        provider=ProviderType(provider.lower()),
        scores=scores,
        metadata=metadata or {"timestamp": "2024-01-01T00:00:00Z"},
        **kwargs,
    )


def test_auto_validate_empty_results():
    report = auto_validate([])
    assert report.valid is False
    assert any("Empty benchmark results" in i.message for i in report.issues)


def test_auto_validate_missing_model_name():
    result = _make_result(model="")
    report = auto_validate([result])
    assert any("Missing model name" in i.message for i in report.issues)


def test_auto_validate_missing_provider():
    result = BenchmarkResult(
        model="m1",
        provider=ProviderType("openrouter"),
        scores=[Score(benchmark=BenchmarkName.GENERAL, raw=0.5, normalized=0.5, weight=1.0, weighted=0.5)],
        metadata={"timestamp": "2024-01-01T00:00:00Z"},
    )
    result.provider = None
    report = auto_validate([result])
    assert any("Missing provider" in i.message for i in report.issues)


def test_auto_validate_with_runs_drift_and_outliers():
    result = _make_result(model="m1")

    run1 = [_make_result(model="m1", scores=[Score(benchmark=BenchmarkName.GENERAL, raw=0.5, normalized=0.5, weight=1.0, weighted=0.5)])]
    run2 = [_make_result(model="m1", scores=[Score(benchmark=BenchmarkName.GENERAL, raw=0.9, normalized=0.9, weight=1.0, weighted=0.9)])]

    fake_stats = type("S", (), {"score_drift": staticmethod(lambda r: {"m1": 0.2}), "outlier_runs": staticmethod(lambda r: [(1, 0.9)])})()
    with patch.dict("sys.modules", {"aibenchmark.app.statistics": fake_stats}):
        report = auto_validate([result], runs=[run1, run2])

    assert any("drift" in i.category for i in report.issues)
    assert any("outlier" in i.category for i in report.issues)


def test_auto_validate_weight_sum_zero():
    result = _make_result()
    result.scores = [Score(benchmark=BenchmarkName.GENERAL, raw=0.5, normalized=0.5, weight=0.0, weighted=0.0)]
    report = auto_validate([result])
    assert any("weights" in i.category and "zero" in i.message for i in report.issues)


def test_auto_validate_discrimination_failure():
    result1 = _make_result(model="m1", scores=[Score(benchmark=BenchmarkName.GENERAL, raw=0.5, normalized=0.5, weight=1.0, weighted=0.5)])
    result2 = _make_result(model="m2", scores=[Score(benchmark=BenchmarkName.GENERAL, raw=0.5, normalized=0.5, weight=1.0, weighted=0.5)])
    report = auto_validate([result1, result2])
    assert any("distinguish" in i.message for i in report.issues)
