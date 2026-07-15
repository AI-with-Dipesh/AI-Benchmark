"""Sprint 9 legacy module coverage tests."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.history import HistoryWriter, load_latest
from aibenchmark.app.models import (
    BenchmarkName,
    BenchmarkResult,
    PluginCategory,
    ProviderCapabilities,
    ProviderType,
    RoutingContext,
    Score,
)
from aibenchmark.app.config import ConfigError
from aibenchmark.app.plugin.registry import PluginCompatibilityWarning, _validate_plugin_metadata, get_manager
from aibenchmark.app.provider_registry import ProviderRegistry
from aibenchmark.app.validation import (
    safe_yaml_load,
    validate_benchmark_name,
    validate_json_schema,
    validate_metadata,
    validate_model_name,
    validate_numeric_range,
    validate_path_safety,
    validate_positive_int,
    validate_provider_name,
    validate_results,
    YAMLSafetyError,
)
from aibenchmark.interfaces.provider import BaseProvider
from aibenchmark.app.model_selector import ModelSelector


# ---------------------------------------------------------------------------
# BaseProvider interface coverage
# ---------------------------------------------------------------------------


class _FakeProvider(BaseProvider):
    plugin_name = "fake"
    provider_type = ProviderType.OLLAMA

    def connect(self) -> None:
        return None

    def list_models(self) -> list[str]:
        return ["model-a"]

    def chat(self, model: str, messages: list[dict[str, str]], **kwargs: Any):
        return MagicMock(content="ok")


def test_base_provider_authenticate_with_provider_type():
    p = _FakeProvider(api_key="k", base_url="http://example.com")
    result = p.authenticate()
    assert result.provider == "ollama"
    assert result.authenticated is True


def test_base_provider_authenticate_without_provider_type():
    class _NoType(_FakeProvider):
        provider_type = None

    p = _NoType(api_key="k", base_url="http://example.com")
    result = p.authenticate()
    assert result.provider == "unknown"
    assert result.authenticated is True


def test_base_provider_health_check_failure_path():
    class _Flaky(BaseProvider):
        def connect(self) -> None:
            raise RuntimeError("boom")

        def list_models(self) -> list[str]:
            return []

        def chat(self, *args: Any, **kwargs: Any):
            return MagicMock(content="ok")

    assert _Flaky(api_key="k").health_check() is False


def test_base_provider_supports_exception_path():
    class _FlakyCaps(BaseProvider):
        def capabilities(self) -> ProviderCapabilities:
            raise RuntimeError("caps boom")

        def connect(self) -> None:
            return None

        def list_models(self) -> list[str]:
            return []

        def chat(self, *args: Any, **kwargs: Any):
            return MagicMock(content="ok")

    assert _FlakyCaps(api_key="k").supports("streaming") is False


def test_base_provider_validate_configuration_missing_fields():
    p = _FakeProvider(api_key="", base_url="")
    issues = p.validate_configuration()
    assert issues["valid"] is False
    assert "Missing API key" in issues["issues"]
    assert "Missing base_url" in issues["issues"]


def test_base_provider_supports_helpers():
    p = _FakeProvider(api_key="k", base_url="http://example.com")
    assert p.supports_streaming() is False
    assert p.supports_tools() is False
    assert p.supports_json() is False
    assert p.supports_context_length() is False


def test_base_provider_estimate_and_invoke():
    p = _FakeProvider(api_key="k", base_url="http://example.com")
    assert p.estimate_tokens("hello world") == 2
    assert p.estimate_cost(10, 5) == 0.0
    response = p.invoke("m", [{"role": "user", "content": "hi"}])
    assert response.content == "ok"
    assert next(p.stream("m", [{"role": "user", "content": "hi"}])) == "ok"


def test_base_provider_parse_rate_limit_various_headers():
    rl = _FakeProvider._parse_rate_limit(
        {
            "x-ratelimit-remaining": "10",
            "x-ratelimit-limit": "20",
            "x-ratelimit-reset": "5",
            "retry-after": "2",
        }
    )
    assert rl.remaining == 10
    assert rl.limit == 20
    assert rl.reset_seconds == 5
    assert rl.retry_after == 2

    rl_ms = _FakeProvider._parse_rate_limit({"x-ms-ratelimit-remaining": "3"})
    assert rl_ms.remaining == 3


# ---------------------------------------------------------------------------
# BenchEngine error-path coverage
# ---------------------------------------------------------------------------


def test_engine_init_config_failure(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "aibenchmark.app.config.AppConfig.__init__",
        lambda self, *args, **kwargs: (_ for _ in ()).throw(ConfigError("bad")),
        raising=False,
    )
    with pytest.raises(RuntimeError, match="Benchmark configuration failed"):
        BenchEngine()


def test_engine_init_provider_missing_api_key(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "aibenchmark.app.engine.AppConfig.provider_config",
        lambda self, name: {"api_key": "", "api_key_env": "TEST_KEY", "base_url": "http://example.com"},
    )
    engine = BenchEngine()
    with pytest.raises(ValueError, match="Missing API key"):
        engine._init_provider("ollama")


def test_engine_generate_reports_missing_reporter(tmp_path: Path):
    engine = BenchEngine()
    results = [
        BenchmarkResult(
            model="m",
            provider=ProviderType.OLLAMA,
            scores=[Score(benchmark=BenchmarkName.LATENCY, raw=1.0, normalized=1.0, weight=1.0)],
        )
    ]
    produced = engine.generate_reports(results, tmp_path, formats=["no-such-reporter"])
    assert produced == {}


def test_engine_run_parallel_disabled():
    engine = BenchEngine()
    with pytest.raises(Exception, match="Parallel execution is disabled"):
        engine.run_parallel(
            ["ollama"], "m", ["general"], [{"role": "user", "content": "hi"}]
        )


# ---------------------------------------------------------------------------
# Validation uncovered paths
# ---------------------------------------------------------------------------


def test_validate_results_empty_results():
    report = validate_results([])
    assert report.valid is False
    assert any(issue.category == "results" for issue in report.issues)


def test_validate_metadata_missing_overall():
    result = BenchmarkResult(
        model="m",
        provider=ProviderType.OLLAMA,
        scores=[Score(benchmark=BenchmarkName.GENERAL, raw=1.0, normalized=1.0, weight=1.0)],
    )
    report = validate_metadata(result)
    assert any(issue.category == "scoring" for issue in report.issues)


def test_validate_path_safety_empty_and_escape():
    report = validate_path_safety("", Path("/tmp"))
    assert report.valid is False

    report = validate_path_safety(Path("/etc"), Path("/tmp"))
    assert report.valid is False


def test_validate_positive_int_non_integer():
    report = validate_positive_int("abc")
    assert report.valid is False


def test_validate_numeric_range_bounds_and_type():
    report = validate_numeric_range(5, min_v=10)
    assert report.valid is False
    report = validate_numeric_range(25, min_v=10, max_v=20)
    assert report.valid is False
    report = validate_numeric_range("abc", min_v=0)
    assert report.valid is False


def test_validate_model_name_suspicious_chars():
    report = validate_model_name("bad*model")
    assert report.valid is False


def test_validate_provider_name_unrecognized():
    report = validate_provider_name("unknown_provider")
    assert report.valid is False


def test_validate_json_schema_edge_cases():
    int_schema = {"type": "integer", "minimum": 0, "maximum": 10}
    assert validate_json_schema(5, int_schema).valid is True
    assert validate_json_schema(20, int_schema).valid is False
    bool_schema = {"type": "boolean"}
    assert validate_json_schema(True, bool_schema).valid is True
    string_schema = {"type": "string", "minLength": 3, "maxLength": 5}
    assert validate_json_schema("ab", string_schema).valid is False
    assert validate_json_schema("abcdef", string_schema).valid is False
    assert validate_json_schema("abc", string_schema).valid is True


def test_yaml_safety_error_wrapping():
    with pytest.raises(YAMLSafetyError):
        safe_yaml_load("key: [unclosed", label="test")


# ---------------------------------------------------------------------------
# Model selector strategy coverage
# ---------------------------------------------------------------------------


def test_model_selector_static_strategies():
    candidates = [
        {"provider": "a", "model": "m1", "estimated_cost": 0.1, "capability_score": 0.9, "history_score": 0.5},
        {"provider": "b", "model": "m2", "estimated_cost": 0.2, "capability_score": 0.7, "history_score": 0.6},
    ]
    ctx = RoutingContext(benchmark_name=BenchmarkName.GENERAL)
    plan = ModelSelector._cost_aware(candidates, ctx)
    assert plan.provider == "a"
    assert plan.model == "m1"

    plan = ModelSelector._capability_first(candidates, ctx)
    assert plan.provider == "a"
    assert plan.model == "m1"


def test_model_selector_round_robin():
    candidates = [
        {"provider": "a", "model": "m1", "estimated_cost": 0.1, "capability_score": 0.9, "history_score": 0.5},
        {"provider": "b", "model": "m2", "estimated_cost": 0.2, "capability_score": 0.7, "history_score": 0.6},
    ]
    ctx = RoutingContext(benchmark_name=BenchmarkName.GENERAL, provider_name="a")
    plan = ModelSelector._round_robin(candidates, ctx)
    assert plan.provider in {"a", "b"}


# ---------------------------------------------------------------------------
# Certification coverage
# ---------------------------------------------------------------------------


def test_certifier_nonexistent_provider_returns_experimental():
    from aibenchmark.app.certification import ProviderCertifier

    certifier = ProviderCertifier()
    report = certifier.certify("no-such-provider")
    assert report.certification_level.value == "experimental"
    assert report.reliability_score == 0.0
    assert report.connection_health is False
    assert report.configuration_valid is False


# ---------------------------------------------------------------------------
# History coverage
# ---------------------------------------------------------------------------


def test_history_writer_and_load_latest(tmp_path: Path):
    HistoryWriter.reset()
    db_path = tmp_path / "history.db"
    writer = HistoryWriter(db_path)
    results = [
        BenchmarkResult(
            model="m",
            provider=ProviderType.OLLAMA,
            scores=[Score(benchmark=BenchmarkName.GENERAL, raw=1.0, normalized=1.0, weight=1.0)],
            overall=1.0,
        )
    ]
    writer.save_run(results, details={"run": 1})
    # Data is on the writer's owned connection; make it visible before reading.
    writer._conn.commit()
    latest = load_latest(1, db_path=db_path)
    assert len(latest) == 1
    assert latest[0][0].model == "m"
    HistoryWriter.reset()


# ---------------------------------------------------------------------------
# Reporter coverage (legacy reporters)
# ---------------------------------------------------------------------------


def _make_result(provider: str = "ollama", model: str = "llama3") -> BenchmarkResult:
    return BenchmarkResult(
        model=model,
        provider=ProviderType(provider),
        scores=[Score(benchmark=BenchmarkName.GENERAL, raw=1.0, normalized=0.9, weight=1.0)],
        estimated_cost=0.01,
    )


def test_optimization_reporter_with_cost(tmp_path: Path):
    from aibenchmark.plugins.reporters.optimization import OptimizationReporter

    reporter = OptimizationReporter()
    reporter.generate([_make_result(), _make_result()], tmp_path / "opt.md")
    text = (tmp_path / "opt.md").read_text(encoding="utf-8")
    assert "Optimization Report" in text
    assert "llama3" in text


def test_optimization_reporter_without_cost(tmp_path: Path):
    from aibenchmark.plugins.reporters.optimization import OptimizationReporter

    no_cost = BenchmarkResult(
        model="m",
        provider=ProviderType.OLLAMA,
        scores=[Score(benchmark=BenchmarkName.GENERAL, raw=1.0, normalized=0.9, weight=1.0)],
    )
    reporter = OptimizationReporter()
    reporter.generate([no_cost], tmp_path / "opt2.md")
    text = (tmp_path / "opt2.md").read_text(encoding="utf-8")
    assert "Available models" in text


def test_routing_reporter_success_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    from aibenchmark.plugins.reporters.routing import RoutingReporter

    plan = MagicMock()
    plan.provider = "ollama"
    plan.model = "m"
    plan.rationale = "rationale"
    plan.fallback_providers = []
    plan.fallback_models = []

    monkeypatch.setattr(
        "aibenchmark.app.model_selector.ModelSelector.select",
        lambda *args, **kwargs: plan,
    )
    reporter = RoutingReporter()
    out = tmp_path / "routing.md"
    reporter.generate([_make_result()], out)
    text = out.read_text(encoding="utf-8")
    assert "Routing Report" in text
    assert "ollama" in text
