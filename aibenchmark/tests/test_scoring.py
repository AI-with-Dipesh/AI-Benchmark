from __future__ import annotations

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, Score


def test_score_weighted_calculation():
    score = Score(benchmark=BenchmarkName.LATENCY, raw=100.0, normalized=0.8, weight=2.0)
    assert score.weighted == 1.6


def test_benchmark_result_calculate_overall():
    result = BenchmarkResult(
        model="test",
        provider="ollama",
        scores=[
            Score(benchmark=BenchmarkName.LATENCY, raw=100.0, normalized=0.8, weight=2.0),
            Score(benchmark=BenchmarkName.CODING, raw=1.0, normalized=1.0, weight=1.0),
        ],
    )
    overall = result.calculate_overall()
    expected = (0.8 * 2.0 + 1.0 * 1.0) / 3.0
    assert abs(overall - expected) < 0.01


def test_benchmark_result_empty_scores():
    result = BenchmarkResult(model="test", provider="ollama")
    assert result.calculate_overall() == 0.0
