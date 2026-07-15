"""Sprint 9 analytics and residual coverage boost."""

from __future__ import annotations

from pathlib import Path

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
    ProviderCapabilities,
    ProviderType,
    Score,
)
from aibenchmark.app.validation import validate_json_schema
from aibenchmark.app.model_selector import ModelSelector


def _make_result(
    model: str = "m",
    provider: str = "ollama",
    benchmark: BenchmarkName = BenchmarkName.GENERAL,
    raw: float = 1.0,
    normalized: float = 1.0,
    weight: float = 1.0,
    overall: float = 1.0,
    metadata: dict[str, object] | None = None,
    details: dict[str, object] | None = None,
    latency_ms: float | None = 120.0,
    prompt_tokens: int = 10,
    completion_tokens: int = 20,
    estimated_cost: float = 0.01,
) -> BenchmarkResult:
    return BenchmarkResult(
        model=model,
        provider=ProviderType(provider),
        scores=[Score(benchmark=benchmark, raw=raw, normalized=normalized, weight=weight)],
        overall=overall,
        metadata={"latency_ms": latency_ms} if latency_ms is not None else {},
        details=details or {},
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        estimated_cost=estimated_cost,
    )


# ---------------------------------------------------------------------------
# analytics.py direct tests
# ---------------------------------------------------------------------------


def test_recommend_empty_results():
    assert recommend([]) == []


def test_recommend_picks_best_available():
    results = [
        _make_result(model="a", provider="ollama", benchmark=BenchmarkName.CODING, normalized=0.8, overall=0.8, latency_ms=120.0),
        _make_result(model="b", provider="nvidia", benchmark=BenchmarkName.CODING, normalized=0.9, overall=0.9, latency_ms=50.0),
    ]
    recs = recommend(results)
    assert len(recs) == 1
    assert recs[0].model == "b"
    assert "Highest category score" in recs[0].reasons


def test_build_trends_two_runs_same_model():
    run1 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8, metadata={"timestamp": "2026-01-01T00:00:00+00:00"})]
    run2 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.9, metadata={"timestamp": "2026-01-02T00:00:00+00:00"})]
    trends = build_trends([run1, run2])
    assert "ollama:m" in trends
    entry = trends["ollama:m"]
    assert entry.overall_change == pytest.approx(0.1)
    assert entry.trend == "improving"


def test_build_trends_single_run_skipped():
    run1 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
    assert build_trends([run1]) == {}


def test_build_comparison_two_runs():
    run1 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.8)]
    run2 = [_make_result(model="m", provider="ollama", benchmark=BenchmarkName.GENERAL, overall=0.9)]
    deltas = build_comparison(run1, run2)
    assert "general" in deltas


def test_best_value_when_no_latency():
    results = [_make_result(model="a", provider="ollama", overall=1.0, latency_ms=None)]
    recommendation = best_value(results)
    assert recommendation is not None
    assert recommendation.model == "a"


def test_fastest_helper():
    results = [_make_result(model="a", provider="ollama", latency_ms=100.0)]
    assert fastest(results) is not None


def test_highest_quality_helper():
    results = [_make_result(model="a", provider="ollama")]
    assert highest_quality(results) is not None


def test_most_stable_helper():
    run1 = [_make_result(model="a", provider="ollama", overall=0.8)]
    run2 = [_make_result(model="a", provider="ollama", overall=0.9)]
    assert most_stable([run1, run2]) is not None


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
# model_selector.py residual coverage
# ---------------------------------------------------------------------------


def test_model_selector_capability_score_empty_required():
    ctx = type("Ctx", (), {"required_capabilities": set()})()
    score = ModelSelector._capability_score(ProviderCapabilities(), ctx)
    assert score == 1.0
