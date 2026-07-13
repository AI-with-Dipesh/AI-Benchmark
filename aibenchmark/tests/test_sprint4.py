from __future__ import annotations

from pathlib import Path

import pytest

from aibenchmark.app.calibration import calibrate
from aibenchmark.app.models import (
    BenchmarkResult,
    CalibrationReport,
    PluginCategory,
    ProviderType,
    RecommendationStability,
    ReliabilityEntry,
    ReliabilityReport,
    Score,
    StatisticSummary,
    TokenUsage,
    ValidationReport,
)
from aibenchmark.app.recommendation_validation import validate_recommendations
from aibenchmark.app.reliability import build_reliability
from aibenchmark.app.statistics import category_stats, outlier_runs, score_drift, summarize
from aibenchmark.app.token_accounting import cost_report, token_report
from aibenchmark.app.validation import validate_metadata, validate_results
from aibenchmark.app.auto_validation import auto_validate


from aibenchmark.app.models import BenchmarkName


def _score(benchmark: str | BenchmarkName, normalized, raw=0.0, weight=1.0):
    bm = BenchmarkName(benchmark) if isinstance(benchmark, str) else benchmark
    return Score(benchmark=bm, raw=raw, normalized=normalized, weight=weight)


def _result(model="m", provider=ProviderType.OLLAMA, **kwargs):
    defaults = dict(scores=[], overall=0.0, details={}, metadata={})
    defaults.update(kwargs)
    return BenchmarkResult(model=model, provider=provider, **defaults)


class TestValidation:
    def test_validate_results_empty(self) -> None:
        report = validate_results([])
        assert not report.valid
        assert any(i.category == "results" for i in report.issues)

    def test_validate_results_no_scores(self) -> None:
        r = _result()
        report = validate_results([r])
        assert any(i.category == "scoring" for i in report.issues)

    def test_validate_results_missing_model(self) -> None:
        r = _result(model="")
        report = validate_results([r])
        assert any(i.category == "results" for i in report.issues)

    def test_validate_metadata_missing_required(self) -> None:
        r = _result(model="", metadata={})
        report = validate_metadata(r)
        assert not report.valid
        assert any(i.category == "metadata" for i in report.issues)

    def test_auto_validate_flags_missing_fields(self) -> None:
        r = _result()
        report = auto_validate([r])
        assert any(i.category == "metadata" for i in report.issues)
        assert any(i.category == "cost" for i in report.issues)


class TestStatistics:
    def test_summarize(self) -> None:
        s = summarize([1.0, 2.0, 3.0])
        assert abs(s.mean - 2.0) < 1e-9
        assert abs(s.median - 2.0) < 1e-9

    def test_summarize_single_value(self) -> None:
        s = summarize([5.0])
        assert s.mean == 5.0
        assert s.std_dev == 0.0
        assert s.sample_count == 1

    def test_summarize_empty(self) -> None:
        s = summarize([])
        assert s.sample_count == 0

    def test_category_stats(self) -> None:
        results = [_result(scores=[_score("coding", 0.8), _score("coding", 0.9)])]
        stats = category_stats(results, "coding")
        assert abs(stats.mean - 0.85) < 1e-9

    def test_outlier_runs_none(self) -> None:
        assert outlier_runs([]) == []

    def test_outlier_runs_detects_outlier(self) -> None:
        r1 = _result(overall=0.9, metadata={"timestamp": "2026-01-01T00:00:00Z"})
        r2 = _result(overall=0.9, metadata={"timestamp": "2026-01-02T00:00:00Z"})
        r3 = _result(overall=-5.0, metadata={"timestamp": "2026-01-03T00:00:00Z"})
        outliers = outlier_runs([[r1], [r2], [r3]], threshold=1.0)
        assert len(outliers) == 1

    def test_score_drift(self) -> None:
        r1 = _result(overall=0.5, metadata={"timestamp": "2026-01-01T00:00:00Z"})
        r2 = _result(overall=0.7, metadata={"timestamp": "2026-01-02T00:00:00Z"})
        drift = score_drift([[r1], [r2]])
        assert drift.get("ollama:m") == pytest.approx(0.2)


class TestReliability:
    def test_build_reliability_success_rates(self) -> None:
        r1 = _result(metadata={"status": "success", "latency_ms": 100.0})
        r2 = _result(metadata={"status": "error", "latency_ms": 0.0})
        report = build_reliability([[r1, r2]])
        entry = report.entries["ollama:m"]
        assert entry.success_rate == 0.5
        assert entry.failure_rate == 0.5

    def test_average_latency(self) -> None:
        r1 = _result(metadata={"status": "success", "latency_ms": 100.0})
        report = build_reliability([[r1]])
        assert report.entries["ollama:m"].average_latency_ms == 100.0

    def test_p95_p99_latency(self) -> None:
        latencies = [float(i) for i in range(1, 101)]
        rows = [_result(metadata={"status": "success", "latency_ms": lat}) for lat in latencies]
        report = build_reliability([rows])
        entry = report.entries["ollama:m"]
        assert entry.p95_latency_ms is not None
        assert entry.p99_latency_ms is not None
        assert entry.p95_latency_ms <= entry.p99_latency_ms

    def test_provider_availability(self) -> None:
        r1 = _result(provider=ProviderType.OLLAMA, metadata={"status": "success"})
        r2 = _result(provider=ProviderType.OLLAMA, metadata={"status": "error"})
        report = build_reliability([[r1, r2]])
        assert "ollama" in report.provider_availability
        assert report.provider_availability["ollama"] == 0.5


class TestTokenAccounting:
    def test_token_report(self) -> None:
        r = _result(prompt_tokens=10, completion_tokens=20, estimated_cost=0.001, metadata={"latency_ms": 100.0})
        report = token_report([r])
        assert report.prompt_tokens == 10
        assert report.completion_tokens == 20
        assert report.total_tokens == 30
        assert report.estimated_cost == 0.001

    def test_token_report_empty(self) -> None:
        report = token_report([])
        assert report.prompt_tokens == 0
        assert report.completion_tokens == 0
        assert report.total_tokens == 0
        assert report.tokens_per_second is None

    def test_cost_report_multi_model(self) -> None:
        r1 = _result(provider=ProviderType.OLLAMA, model="m1", prompt_tokens=10, completion_tokens=20, estimated_cost=0.001)
        r2 = _result(provider=ProviderType.OLLAMA, model="m2", prompt_tokens=5, completion_tokens=10, estimated_cost=0.002)
        report = cost_report([[r1], [r2]])
        assert report.total_cost == 0.003
        assert "m1" in report.by_model
        assert "m2" in report.by_model
        assert report.by_model["m1"] == 0.001
        assert report.by_model["m2"] == 0.002


class TestCalibration:
    def test_calibrate_detects_bias(self) -> None:
        # category coding consistently high vs others
        r1 = _result(scores=[_score("coding", 0.95)], overall=0.95)
        r2 = _result(scores=[_score("coding", 0.92)], overall=0.92)
        r3 = _result(scores=[_score("reasoning", 0.5)], overall=0.5)
        report = calibrate([[r1, r2], [r3]])
        assert any(i.category == "bias" for i in report.issues)

    def test_calibration_report_fields(self) -> None:
        r1 = _result(scores=[_score("coding", 0.8)], overall=0.8)
        report = calibrate([[r1]])
        assert isinstance(report, CalibrationReport)
        assert "coding" in report.category_bias


class TestRecommendationValidation:
    def test_stable_recommendations(self) -> None:
        r1 = _result(scores=[_score("coding", 0.9)], overall=0.9)
        r2 = _result(scores=[_score("coding", 0.88)], overall=0.88)
        stability = validate_recommendations([[r1], [r2]])
        assert isinstance(stability, RecommendationStability)


class TestEngineRetryTimeout:
    def test_retry_count_respected(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setenv("OLLAMA_API_KEY", "fake")
        from aibenchmark.app.engine import BenchEngine
        from aibenchmark.app.models import PluginCategory, ProviderType, ResponseObject

        engine = BenchEngine()

        class FakeProvider:
            provider_type = ProviderType.OLLAMA

            def __init__(self, api_key: str, base_url: str = "", **kwargs):
                self.api_key = api_key
                self.base_url = base_url
                self.calls = 0

            def chat(self, model: str, messages: list[dict[str, str]], **kwargs):
                self.calls += 1
                raise TimeoutError("fake timeout")

        engine.plugins.register(PluginCategory.PROVIDER, "ollama", FakeProvider)
        engine.retry_policy = type(engine.retry_policy)(retry_count=2, backoff_factor=0)
        engine.timeout_policy = type(engine.timeout_policy)(request_timeout_seconds=60.0)
        result = engine.run_benchmark("ollama", "m", BenchmarkName.LATENCY, [{"role": "user", "content": "hi"}])
        assert result.retry_count == 2
        assert result.timeout_status == "request"

    def test_non_retryable_exception_fails_immediately(self, monkeypatch) -> None:
        monkeypatch.setenv("OLLAMA_API_KEY", "fake")
        from aibenchmark.app.engine import BenchEngine
        from aibenchmark.app.models import PluginCategory, ProviderType

        engine = BenchEngine()

        class FakeProvider:
            provider_type = ProviderType.OLLAMA

            def __init__(self, api_key: str, base_url: str = "", **kwargs):
                self.api_key = api_key
                self.base_url = base_url
                self.calls = 0

            def chat(self, model: str, messages: list[dict[str, str]], **kwargs):
                self.calls += 1
                raise ValueError("always fails")

        engine.plugins.register(PluginCategory.PROVIDER, "ollama", FakeProvider)
        engine.retry_policy = type(engine.retry_policy)(retry_count=3, backoff_factor=0)
        engine.timeout_policy = type(engine.timeout_policy)(request_timeout_seconds=60.0)
        result = engine.run_benchmark("ollama", "m", BenchmarkName.LATENCY, [{"role": "user", "content": "hi"}])
        assert result.retry_count == 0
        assert result.metadata.get("status") == "error"

    def test_string_benchmark_name_converts(self, monkeypatch, tmp_path: Path) -> None:
        monkeypatch.setenv("OLLAMA_API_KEY", "fake")
        from aibenchmark.app.engine import BenchEngine
        from aibenchmark.app.models import PluginCategory, ProviderType, ResponseObject

        engine = BenchEngine()

        class FakeProvider:
            provider_type = ProviderType.OLLAMA

            def __init__(self, api_key: str, base_url: str = "", **kwargs):
                self.api_key = api_key
                self.base_url = base_url

            def chat(self, model: str, messages: list[dict[str, str]], **kwargs):
                return ResponseObject(
                    provider=self.provider_type,
                    model=model,
                    content="pong",
                    latency_ms=10.0,
                    tokens_in=1,
                    tokens_out=2,
                )

        engine.plugins.register(PluginCategory.PROVIDER, "ollama", FakeProvider)
        result = engine.run_benchmark("ollama", "m", "latency", [{"role": "user", "content": "hi"}])
        assert result.overall >= 0.0


class TestValidationEdgeCases:
    def test_validate_results_zero_weights(self) -> None:
        r = _result(scores=[_score("coding", 0.0, weight=0.0)])
        report = validate_results([r])
        assert any(i.category == "weights" for i in report.issues)

    def test_validate_metadata_valid(self) -> None:
        r = _result(model="m", metadata={"timestamp": "2026-01-01T00:00:00Z"})
        report = validate_metadata(r)
        assert report.valid

    def test_auto_validate_valid_result(self) -> None:
        r = _result(
            scores=[_score("coding", 0.8)],
            evaluation="strong",
            objective_validation=0.9,
            confidence=0.85,
            retry_count=0,
            timeout_status=None,
            prompt_tokens=1,
            completion_tokens=1,
            model_version="1.0",
            benchmark_version="0.4.0",
            metadata={"timestamp": "2026-01-01T00:00:00Z"},
        )
        report = auto_validate([r])
        assert not any(i.category == "metadata" for i in report.issues if i.severity == "critical")

    def test_auto_validate_flags_missing_sprint4_fields(self) -> None:
        r = _result(
            scores=[_score("coding", 0.8)],
            metadata={"timestamp": "2026-01-01T00:00:00Z"},
        )
        report = auto_validate([r])
        categories = {i.category for i in report.issues}
        assert "evaluation" in categories
        assert "validation" in categories
        assert "confidence" in categories
