"""Sprint 9 coverage gap tests for residual uncovered lines."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest
import yaml

from aibenchmark.app.analytics import (
    best_value,
    build_comparison,
    build_trends,
    fastest,
    highest_quality,
    most_stable,
    recommend,
)
from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.models import (
    BenchmarkName,
    BenchmarkResult,
    PluginCategory,
    ProviderCapabilities,
    ProviderType,
    ResponseObject,
    RoutingContext,
    Score,
)
from aibenchmark.app.validation import validate_json_schema
from aibenchmark.app.model_selector import ModelSelector
from aibenchmark.app.history import HistoryWriter, load_latest, load_run, save_run
from aibenchmark.plugins.reporters.provider_comparison import ProviderComparisonReporter


# ---------------------------------------------------------------------------
# analytics.py residual coverage
# ---------------------------------------------------------------------------


def _make_result(
    model: str = "m",
    provider: str = "ollama",
    benchmark: BenchmarkName = BenchmarkName.GENERAL,
    raw: float = 1.0,
    normalized: float = 1.0,
    weight: float = 1.0,
    overall: float = 1.0,
    metadata: dict[str, Any] | None = None,
    details: dict[str, Any] | None = None,
    latency_ms: float | None = 120.0,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    estimated_cost: float | None = 0.01,
) -> BenchmarkResult:
    return BenchmarkResult(
        model=model,
        provider=ProviderType(provider),
        scores=[Score(benchmark=benchmark, raw=raw, normalized=normalized, weight=weight)],
        overall=overall,
        metadata=metadata or {"latency_ms": latency_ms},
        details=details or {},
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=estimated_cost,
    )


def test_recommend_empty_results():
    assert recommend([]) == []


def test_recommend_strong_all_round():
    results = [
        _make_result(
            model="a",
            provider="ollama",
            benchmark=BenchmarkName.CODING,
            normalized=0.95,
            overall=0.95,
            latency_ms=120.0,
        ),
        _make_result(
            model="b",
            provider="nvidia",
            benchmark=BenchmarkName.CODING,
            normalized=0.8,
            overall=0.8,
            latency_ms=50.0,
        ),
    ]
    recs = recommend(results)
    assert recs
    best = recs[0]
    assert best.model == "a"
    assert "Strong all-round performance" in best.reasons


def test_build_trends_two_runs():
    HistoryWriter.reset()
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "history.db"
        run1 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
        run2 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.9)]
        save_run(run1, db_path=db_path)
        save_run(run2, db_path=db_path)
        runs = [run1, run2]
        trends = build_trends(runs)
        key = "ollama:m"
        assert key in trends
        entry = trends[key]
        assert entry.overall_change == pytest.approx(0.1)
    HistoryWriter.reset()


def test_build_comparison_two_runs():
    run1 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
    run2 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.9)]
    deltas = build_comparison(run1, run2)
    assert isinstance(deltas, dict)


def test_analytics_helpers_none_paths():
    result_no_meta = BenchmarkResult(
        model="m",
        provider=ProviderType.OLLAMA,
        scores=[Score(benchmark=BenchmarkName.GENERAL, raw=1.0, normalized=1.0, weight=1.0)],
    )
    from aibenchmark.app.analytics import _parse_latency, _reliability_score

    assert _parse_latency(result_no_meta) is None
    assert _reliability_score(result_no_meta) is None


# ---------------------------------------------------------------------------
# config.py invalid inputs
# ---------------------------------------------------------------------------


def test_appconfig_missing_providers(tmp_path: Path):
    with pytest.raises(ConfigError, match="Missing providers config"):
        AppConfig(tmp_path)


def test_appconfig_missing_benchmark(tmp_path: Path):
    (tmp_path / "providers.yaml").write_text("{}", encoding="utf-8")
    with pytest.raises(ConfigError, match="Missing benchmark config"):
        AppConfig(tmp_path)


def test_appconfig_invalid_providers_yaml(tmp_path: Path):
    (tmp_path / "providers.yaml").write_text("- not_a_mapping", encoding="utf-8")
    (tmp_path / "benchmark.yaml").write_text("benchmark_version: \"1.0.0\"\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="Invalid providers config"):
        AppConfig(tmp_path)


# ---------------------------------------------------------------------------
# validation.py residual schema branches
# ---------------------------------------------------------------------------


def test_validate_json_schema_array_type_mismatch():
    schema = {"type": "array", "items": {"type": "string"}}
    report = validate_json_schema([1, 2], schema)
    assert report.valid is False


def test_validate_json_schema_string_type_mismatch():
    schema = {"type": "string"}
    report = validate_json_schema(123, schema)
    assert report.valid is False


def test_validate_json_schema_integer_type_mismatch():
    schema = {"type": "integer"}
    report = validate_json_schema(3.14, schema)
    assert report.valid is False


def test_validate_json_schema_number_type_mismatch():
    schema = {"type": "number"}
    report = validate_json_schema("abc", schema)
    assert report.valid is False


def test_validate_json_schema_boolean_type_mismatch():
    schema = {"type": "boolean"}
    report = validate_json_schema(1, schema)
    assert report.valid is False


def test_validate_json_schema_enum_fallback():
    schema = {"type": "string", "enum": ["ok", "fail"]}
    report = validate_json_schema("unknown", schema)
    assert report.valid is False


def test_validate_json_schema_object_additional_properties():
    schema = {"type": "object", "additionalProperties": False, "properties": {"a": {"type": "string"}}}
    report = validate_json_schema({"a": "ok", "b": 1}, schema)
    assert report.valid is False


# ---------------------------------------------------------------------------
# provider_comparison.py residual coverage
# ---------------------------------------------------------------------------


def test_provider_comparison_reporter_without_results(tmp_path: Path):
    reporter = ProviderComparisonReporter()
    fake_comparison = {
        "providers": [],
        "models": {},
        "overall_ranking": [],
        "capabilities": {},
        "health": {},
        "metadata": {},
    }
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(
        "aibenchmark.plugins.reporters.provider_comparison.CrossProviderBenchmark.compare_with_results",
        lambda self, providers, models, results: fake_comparison,
    )
    monkeypatch.setattr(
        "aibenchmark.plugins.reporters.provider_comparison.CrossProviderBenchmark.compare_providers",
        lambda self, providers, models: fake_comparison,
    )
    try:
        out = tmp_path / "provider_comparison.md"
        reporter.generate([], out)
        text = out.read_text(encoding="utf-8")
        assert "Provider Comparison Report" in text
    finally:
        monkeypatch.undo()


# ---------------------------------------------------------------------------
# model_selector.py residual coverage
# ---------------------------------------------------------------------------


def test_model_selector_capability_score_empty_required():
    ctx = RoutingContext(benchmark_name=BenchmarkName.GENERAL)
    score = ModelSelector._capability_score(ProviderCapabilities(), ctx)
    assert score == 1.0


# ---------------------------------------------------------------------------
# history.py residual coverage
# ---------------------------------------------------------------------------


def test_history_load_run_missing(tmp_path: Path):
    HistoryWriter.reset()
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "history.db"
        with pytest.raises(KeyError, match="Run 1 not found"):
            load_run(1, db_path=db_path)
    HistoryWriter.reset()


def test_history_save_run_empty_results(tmp_path: Path):
    with tempfile.TemporaryDirectory() as td:
        db_path = Path(td) / "history.db"
        with pytest.raises(ValueError, match="Cannot save empty results"):
            save_run([], db_path=db_path)
