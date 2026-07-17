"""Sprint 11 coverage expansion for engine.py and analytics.py uncovered paths."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from aibenchmark.app.analytics import _parse_latency, recommend
from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, RoutingPlan, Score


def _make_result(
    provider: str = "ollama",
    model: str = "llama3",
    benchmark: str = "coding",
    normalized: float = 0.8,
    overall: float | None = None,
    latency_ms: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> BenchmarkResult:
    return BenchmarkResult(
        provider=ProviderType(provider),
        model=model,
        scores=[Score(benchmark=BenchmarkName(benchmark), raw=normalized, normalized=normalized, weight=1.0)],
        overall=overall if overall is not None else normalized,
        metadata=metadata or {"timestamp": "2026-01-01T00:00:00+00:00", "latency_ms": latency_ms},
    )


class TestEngineUncoveredPaths:
    def test_fallback_attempts_default_provider_first(self) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.routing = {"fallback": {"strategy": "unknown"}}
        plan = RoutingPlan(provider="a", model="m1", fallback_providers=["b", "c"], fallback_models=["m2"])
        attempts = engine._fallback_attempts(plan, "a", "m1")
        assert attempts == [("b", "m1"), ("c", "m1")]

    def test_execute_fallback_circuit_open_skips(self) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine._is_circuit_open = lambda name: name == "b"
        fake_result = _make_result()
        engine.run_benchmark = MagicMock(return_value=fake_result)
        plan = RoutingPlan(provider="a", model="m1", fallback_providers=["b", "c"], fallback_models=[])
        result = engine._execute_fallback(plan, "a", "m1", BenchmarkName.CODING, [], {}, 0)
        assert result is fake_result
        engine.run_benchmark.assert_called_once_with("c", "m1", BenchmarkName.CODING, [], _fallback_depth=1)

    def test_execute_fallback_exception_continues(self) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine._is_circuit_open = lambda name: False
        engine.run_benchmark = MagicMock(side_effect=RuntimeError("boom"))
        plan = RoutingPlan(provider="a", model="m1", fallback_providers=["b"], fallback_models=[])
        result = engine._execute_fallback(plan, "a", "m1", BenchmarkName.CODING, [], {}, 0)
        assert result is None
        assert engine.run_benchmark.call_count == 1

    def test_init_provider_unknown_raises(self) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.plugins = MagicMock()
        engine.plugins.get.return_value = None
        with pytest.raises(ValueError, match="Unknown provider"):
            engine._init_provider("nonexistent")

    def test_init_provider_instantiation_error_wraps(self) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.plugins = MagicMock()
        engine.plugins.get.return_value = lambda: (_ for _ in ()).throw(RuntimeError("bad init"))
        engine.config = MagicMock()
        engine.config.provider_config.return_value = {"api_key": "x", "base_url": "u"}
        with pytest.raises(RuntimeError, match="Failed to initialize provider"):
            engine._init_provider("ollama")

    def test_load_prompt_none_returns_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        fake_loader = MagicMock()
        fake_loader.load.return_value = None
        monkeypatch.setattr("aibenchmark.app.prompts.PromptLoader", lambda: fake_loader)
        engine.config = MagicMock()
        result = engine._load_prompt(BenchmarkName.CODING)
        assert result == {}

    def test_apply_run_defaults_sets_seed(self) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.run_defaults = {"temperature": 0.7, "seed": 42}
        kwargs: dict[str, Any] = {}
        result = engine._apply_run_defaults(kwargs)
        assert result["seed"] == 42
        assert result["temperature"] == 0.7

    def test_populate_metadata_cost_estimation_failure(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.model_cost.side_effect = RuntimeError("model_cost down")
        engine.config.prompt_version.return_value = "v1"
        engine.config.benchmark_version = "v2"
        engine.config.run_defaults = {"temperature": 0.0, "top_p": 1.0, "seed": None}
        result = BenchmarkResult(model="m", provider=ProviderType.OLLAMA, scores=[], metadata={})
        engine._populate_metadata(result, None, 0.0, BenchmarkName.CODING)
        assert result.model_version is None
        assert result.benchmark_version == "v2"

    def test_run_benchmark_unknown_benchmark_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine._init_provider = MagicMock(return_value=MagicMock())
        engine._health_tracker = MagicMock()
        monkeypatch.setattr(engine, "_load_prompt", MagicMock(return_value={"system": "s", "user": "u"}))
        engine.plugins = MagicMock()
        engine.plugins.get.return_value = None
        with pytest.raises(ValueError, match="Unknown benchmark"):
            engine.run_benchmark("ollama", "m", BenchmarkName.CODING, [])

    def test_run_benchmark_timeout_breaks_retry_loop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.routing = {"fallback_chain": []}
        engine.retry_policy = MagicMock(retry_count=0, backoff_factor=0, retryable=[])
        engine.timeout_policy = MagicMock(request_timeout_seconds=0.001)
        engine._health_tracker = MagicMock()
        provider = MagicMock()
        provider.chat.side_effect = TimeoutError("slow")
        engine._init_provider = MagicMock(return_value=provider)
        monkeypatch.setattr(engine, "_load_prompt", MagicMock(return_value={"system": "s", "user": "u"}))
        engine.plugins = MagicMock()
        engine.plugins.get.return_value = lambda: MagicMock()
        engine.apply_policy = MagicMock(return_value={"provider": "ollama", "model": "m", "fallback_providers": []})
        engine._execute_fallback = MagicMock(return_value=None)
        result = engine.run_benchmark("ollama", "m", BenchmarkName.CODING, [{"role": "user", "content": "hi"}])
        assert result.timeout_status == "request"
        assert result.retry_count >= 0

    def test_run_benchmark_connection_error_not_retryable_breaks(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.routing = {"fallback_chain": []}
        engine.retry_policy = MagicMock(retry_count=0, backoff_factor=0, retryable=[])
        engine.timeout_policy = MagicMock(request_timeout_seconds=60.0)
        engine._health_tracker = MagicMock()
        provider = MagicMock()
        provider.chat.side_effect = ConnectionError("reset")
        engine._init_provider = MagicMock(return_value=provider)
        monkeypatch.setattr(engine, "_load_prompt", MagicMock(return_value={"system": "s", "user": "u"}))
        engine.plugins = MagicMock()
        engine.plugins.get.return_value = lambda: MagicMock()
        engine.apply_policy = MagicMock(return_value={"provider": "ollama", "model": "m", "fallback_providers": []})
        engine._execute_fallback = MagicMock(return_value=None)
        result = engine.run_benchmark("ollama", "m", BenchmarkName.CODING, [{"role": "user", "content": "hi"}])
        assert result.details.get("error_type") == "ConnectionError"

    def test_run_benchmark_benchmark_exception_returns_error_result(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.routing = {"fallback_chain": []}
        engine.retry_policy = MagicMock(retry_count=0, backoff_factor=0)
        engine.timeout_policy = MagicMock(request_timeout_seconds=60.0)
        engine._health_tracker = MagicMock()
        provider = MagicMock()
        provider.chat.return_value = MagicMock()
        engine._init_provider = MagicMock(return_value=provider)
        monkeypatch.setattr(engine, "_load_prompt", MagicMock(return_value={"system": "s", "user": "u"}))
        engine.plugins = MagicMock()
        benchmark_cls = MagicMock()
        benchmark_cls.return_value.run.side_effect = RuntimeError("benchmark boom")
        engine.plugins.get.return_value = benchmark_cls
        result = engine.run_benchmark("ollama", "m", BenchmarkName.CODING, [{"role": "user", "content": "hi"}])
        assert result.details.get("error") == "benchmark boom"
        assert result.scores == []

    def test_generate_reports_cost_reporter_invocation(self, tmp_path: Path) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.model_cost.return_value = (0.001, 0.002)
        reporter_cls = MagicMock()
        engine.plugins = MagicMock()
        engine.plugins.get.return_value = reporter_cls
        engine.generate_reports([_make_result()], tmp_path, formats=["cost"])
        reporter_cls.assert_called_once()
        call_kwargs = reporter_cls.return_value.generate.call_args[1]
        assert "price_lookup" in call_kwargs

    def test_run_parallel_empty_input_returns_empty(self) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.routing = {"parallel": {"enabled": True, "max_workers": 2}}
        result = engine.run_parallel([], "m", [], [])
        assert result == []


class TestAnalyticsUncoveredPaths:
    def test_recommend_no_candidates_for_category(self) -> None:
        results = [
            _make_result(benchmark="coding", normalized=0.9),
            _make_result(benchmark="reasoning", normalized=0.9),
        ]
        recs = recommend(results)
        assert recs

    def test_parse_latency_non_numeric_returns_none(self) -> None:
        result = _make_result(metadata={"latency_ms": "not-a-number"})
        assert _parse_latency(result) is None

    def test_parse_latency_none_returns_none(self) -> None:
        result = _make_result(metadata={})
        assert _parse_latency(result) is None

    def test_build_trends_single_run_no_trend(self) -> None:
        run = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
        from aibenchmark.app.analytics import build_trends
        trends = build_trends([run])
        assert trends == {}

    def test_build_comparison_mismatched_categories(self) -> None:
        run_a = [_make_result(benchmark="coding", overall=0.8)]
        run_b = [_make_result(benchmark="reasoning", overall=0.9)]
        from aibenchmark.app.analytics import build_comparison
        deltas = build_comparison(run_a, run_b)
        assert isinstance(deltas, dict)


# ============================================================
# Sprint 11.5: Regression tests for benchmark scoring defects
# ============================================================

class TestScoreNormalizationPreservation:
    """Regression tests for engine score reconstruction bug.

    Bug: BenchEngine reconstructed Score from result.details, losing normalized
    values because benchmark plugins store details as
    {"raw_score": ..., **metadata} without "normalized".
    This caused normalized=0.0 for all non-latency benchmarks.
    """

    def test_engine_preserves_benchmark_computed_normalized(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.weight.return_value = 25.0
        engine.config.run_defaults = {"temperature": 0.2, "top_p": 0.95, "seed": None}
        engine.config.model_cost.return_value = (0.0, 0.0)
        engine.config.prompt_version.return_value = "1.0"
        engine.config.benchmark_version = "1.3.0"
        engine.retry_policy = MagicMock(retry_count=0, backoff_factor=0)
        engine.timeout_policy = MagicMock(request_timeout_seconds=60.0)
        engine._health_tracker = MagicMock()

        fake_response = MagicMock()
        fake_response.latency_ms = 100.0
        fake_response.tokens_in = 10
        fake_response.tokens_out = 20
        fake_response.model = "test-model"
        fake_response.provider = MagicMock(value="openrouter")
        provider = MagicMock()
        provider.chat.return_value = fake_response
        engine._init_provider = MagicMock(return_value=provider)
        monkeypatch.setattr(engine, "_load_prompt", MagicMock(return_value={"system": "s", "user": "u"}))
        engine.plugins = MagicMock()

        original_score = Score(
            benchmark=BenchmarkName.CODING,
            raw=0.65,
            normalized=0.82,
            weight=1.0,
        )
        benchmark_result = BenchmarkResult(
            model="test-model",
            provider=MagicMock(value="openrouter"),
            scores=[original_score],
            details={"raw_score": 0.65, "syntax_ok": True},
        )
        benchmark_cls = MagicMock(return_value=MagicMock(run=MagicMock(return_value=benchmark_result)))
        engine.plugins.get.return_value = benchmark_cls

        result = engine.run_benchmark(
            "openrouter", "test-model", BenchmarkName.CODING, [{"role": "user", "content": "hi"}]
        )
        assert len(result.scores) == 1
        assert result.scores[0].normalized == 0.82, f"Expected normalized=0.82, got {result.scores[0].normalized}"
        assert result.scores[0].raw == 0.65
        assert result.scores[0].weight == 25.0
        assert result.scores[0].weighted == pytest.approx(20.5)
        assert result.overall == pytest.approx(20.5 / 25.0)

    def test_engine_recalculates_overall_from_preserved_scores(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.weight.return_value = 25.0
        engine.config.run_defaults = {"temperature": 0.2, "top_p": 0.95, "seed": None}
        engine.config.model_cost.return_value = (0.0, 0.0)
        engine.config.prompt_version.return_value = "1.0"
        engine.config.benchmark_version = "1.3.0"
        engine.retry_policy = MagicMock(retry_count=0, backoff_factor=0)
        engine.timeout_policy = MagicMock(request_timeout_seconds=60.0)
        engine._health_tracker = MagicMock()

        fake_response = MagicMock()
        fake_response.latency_ms = 100.0
        fake_response.tokens_in = 10
        fake_response.tokens_out = 20
        fake_response.model = "test-model"
        fake_response.provider = MagicMock(value="openrouter")
        provider = MagicMock()
        provider.chat.return_value = fake_response
        engine._init_provider = MagicMock(return_value=provider)
        monkeypatch.setattr(engine, "_load_prompt", MagicMock(return_value={"system": "s", "user": "u"}))
        engine.plugins = MagicMock()

        original_score = Score(
            benchmark=BenchmarkName.CODING,
            raw=0.5,
            normalized=0.75,
            weight=1.0,
        )
        benchmark_result = BenchmarkResult(
            model="test-model",
            provider=MagicMock(value="openrouter"),
            scores=[original_score],
            details={"raw_score": 0.5},
        )
        benchmark_cls = MagicMock(return_value=MagicMock(run=MagicMock(return_value=benchmark_result)))
        engine.plugins.get.return_value = benchmark_cls

        result = engine.run_benchmark(
            "openrouter", "test-model", BenchmarkName.CODING, [{"role": "user", "content": "hi"}]
        )
        # overall should equal normalized because there's only one score with weight=25
        expected_overall = 0.75
        assert result.overall == pytest.approx(expected_overall), (
            f"Expected overall={expected_overall}, got {result.overall}"
        )

    def test_engine_fallback_reconstruction_when_scores_empty(self, monkeypatch: pytest.MonkeyPatch) -> None:
        engine = BenchEngine.__new__(BenchEngine)
        engine.config = MagicMock()
        engine.config.weight.return_value = 25.0
        engine.config.run_defaults = {"temperature": 0.2, "top_p": 0.95, "seed": None}
        engine.config.model_cost.return_value = (0.0, 0.0)
        engine.config.prompt_version.return_value = "1.0"
        engine.config.benchmark_version = "1.3.0"
        engine.retry_policy = MagicMock(retry_count=0, backoff_factor=0)
        engine.timeout_policy = MagicMock(request_timeout_seconds=60.0)
        engine._health_tracker = MagicMock()

        fake_response = MagicMock()
        fake_response.latency_ms = 100.0
        fake_response.tokens_in = 10
        fake_response.tokens_out = 20
        fake_response.model = "test-model"
        fake_response.provider = MagicMock(value="openrouter")
        provider = MagicMock()
        provider.chat.return_value = fake_response
        engine._init_provider = MagicMock(return_value=provider)
        monkeypatch.setattr(engine, "_load_prompt", MagicMock(return_value={"system": "s", "user": "u"}))
        engine.plugins = MagicMock()

        # Benchmark plugin with empty scores but normalized in details
        benchmark_result = BenchmarkResult(
            model="test-model",
            provider=MagicMock(value="openrouter"),
            scores=[],
            details={"raw_score": 0.7, "normalized": 0.85},
        )
        benchmark_cls = MagicMock(return_value=MagicMock(run=MagicMock(return_value=benchmark_result)))
        engine.plugins.get.return_value = benchmark_cls

        result = engine.run_benchmark(
            "openrouter", "test-model", BenchmarkName.CODING, [{"role": "user", "content": "hi"}]
        )
        assert len(result.scores) == 1
        assert result.scores[0].normalized == 0.85
        assert result.scores[0].raw == 0.7


class TestValidationFalsePositiveFix:
    """Regression tests for validate_metadata zero-overall false positive.

    Bug: validate_metadata used `not result.overall` which flagged valid
    zero scores as "Overall score not calculated".
    """

    def test_validate_metadata_zero_overall_not_flagged(self) -> None:
        from aibenchmark.app.validation import validate_metadata

        result = BenchmarkResult(
            model="test-model",
            provider=ProviderType.OLLAMA,
            scores=[Score(benchmark=BenchmarkName.CODING, raw=0.0, normalized=0.0, weight=1.0)],
            overall=0.0,
            metadata={"timestamp": "2026-01-01T00:00:00+00:00"},
        )
        report = validate_metadata(result)
        scoring_issues = [i for i in report.issues if i.category == "scoring"]
        assert len(scoring_issues) == 0, f"Expected no scoring issues for zero overall, got {scoring_issues}"

    def test_validate_metadata_none_overall_is_flagged(self) -> None:
        from aibenchmark.app.validation import validate_metadata

        result = BenchmarkResult(
            model="test-model",
            provider=ProviderType.OLLAMA,
            scores=[Score(benchmark=BenchmarkName.CODING, raw=0.0, normalized=0.0, weight=1.0)],
            overall=None,
            metadata={"timestamp": "2026-01-01T00:00:00+00:00"},
        )
        report = validate_metadata(result)
        scoring_issues = [i for i in report.issues if i.category == "scoring"]
        assert len(scoring_issues) == 1
        assert "not calculated" in scoring_issues[0].message or "Overall" in scoring_issues[0].message
