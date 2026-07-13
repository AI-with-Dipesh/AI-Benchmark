from __future__ import annotations

from pathlib import Path

import pytest

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score, ValidationIssue
from aibenchmark.app.validation import validate_results, validate_metadata
from aibenchmark.app.auto_validation import auto_validate
from aibenchmark.app.recommendation_validation import validate_recommendations
from aibenchmark.app.statistics import summarize, category_stats, outlier_runs, score_drift
from aibenchmark.app.reliability import build_reliability
from aibenchmark.app.token_accounting import token_report, cost_report
from aibenchmark.app.calibration import calibrate
from aibenchmark.plugins.reporters.sprint4 import (
    generate_validation,
    generate_calibration,
    generate_reliability,
    generate_statistics,
    generate_tokens,
    generate_cost,
    generate_metadata,
)


def _score(benchmark: str | BenchmarkName, normalized, raw=0.0, weight=1.0):
    bm = BenchmarkName(benchmark) if isinstance(benchmark, str) else benchmark
    return Score(benchmark=bm, raw=raw, normalized=normalized, weight=weight)


def _result(model="m", provider=ProviderType.OLLAMA, **kwargs):
    defaults = dict(scores=[], overall=0.0, details={}, metadata={})
    defaults.update(kwargs)
    return BenchmarkResult(model=model, provider=provider, **defaults)


class TestSprint4Reporters:
    def test_validation_reporter_writes_file(self, tmp_path: Path):
        results = [_result(scores=[_score("coding", 0.8)])]
        generate_validation(results, tmp_path / "results.validation")
        text = (tmp_path / "results.validation").read_text()
        assert "Validation Report" in text

    def test_calibration_reporter_writes_file(self, tmp_path: Path):
        results = [_result(scores=[_score("coding", 0.8)], overall=0.8)]
        generate_calibration(results, tmp_path / "results.calibration", runs=[results])
        text = (tmp_path / "results.calibration").read_text()
        assert "Calibration Report" in text
        assert "Inflation factor" in text

    def test_reliability_reporter_writes_file(self, tmp_path: Path):
        results = [_result(metadata={"status": "success", "latency_ms": 100.0})]
        generate_reliability(results, tmp_path / "results.reliability", runs=[results])
        text = (tmp_path / "results.reliability").read_text()
        assert "Reliability Report" in text

    def test_tokens_reporter_writes_file(self, tmp_path: Path):
        results = [_result(prompt_tokens=10, completion_tokens=20, metadata={"latency_ms": 100.0})]
        generate_tokens(results, tmp_path / "results.tokens", runs=[results])
        text = (tmp_path / "results.tokens").read_text()
        assert "Token Usage Report" in text

    def test_cost_reporter_writes_file(self, tmp_path: Path):
        results = [_result(prompt_tokens=10, completion_tokens=20)]
        generate_cost(results, tmp_path / "results.cost", runs=[results])
        text = (tmp_path / "results.cost").read_text()
        assert "Cost Report" in text

    def test_metadata_reporter_writes_file(self, tmp_path: Path):
        results = [_result(prompt_tokens=10, completion_tokens=20)]
        generate_metadata(results, tmp_path / "results.metadata")
        text = (tmp_path / "results.metadata").read_text()
        assert "Benchmark Metadata" in text

    def test_statistics_reporter_single_run(self, tmp_path: Path):
        results = [_result(scores=[_score("coding", 0.8)])]
        generate_statistics(results, tmp_path / "results.statistics")
        text = (tmp_path / "results.statistics").read_text()
        assert "Statistical Summary" in text
        assert "coding" in text

    def test_statistics_reporter_empty(self, tmp_path: Path):
        generate_statistics([], tmp_path / "results.statistics")
        text = (tmp_path / "results.statistics").read_text()
        assert "No data" in text


class TestSprint4ReportersMultiRun:
    def test_statistics_cross_run_drift(self, tmp_path: Path):
        r1 = [_result(overall=0.5, scores=[_score("coding", 0.5)], metadata={"timestamp": "2026-01-01T00:00:00Z"})]
        r2 = [_result(overall=0.7, scores=[_score("coding", 0.7)], metadata={"timestamp": "2026-01-02T00:00:00Z"})]
        generate_statistics(r1, tmp_path / "results.statistics", runs=[r1, r2])
        text = (tmp_path / "results.statistics").read_text()
        assert "Cross-Run Metrics" in text


class TestValidationModule:
    def test_validate_results_discrimination(self) -> None:
        results = [
            _result(scores=[_score("coding", 0.8)], overall=0.8),
            _result(scores=[_score("coding", 0.8)], overall=0.8),
        ]
        report = validate_results(results)
        assert any(i.category == "discrimination" for i in report.issues)

    def test_validate_metadata_valid(self) -> None:
        r = _result(model="m", metadata={"timestamp": "2026-01-01T00:00:00Z"})
        report = validate_metadata(r)
        assert report.valid

    def test_validate_metadata_missing_timestamp(self) -> None:
        r = _result(model="m", metadata={})
        report = validate_metadata(r)
        assert not report.valid
        assert any(i.category == "metadata" for i in report.issues)


class TestAutoValidationModule:
    def test_auto_validate_valid(self) -> None:
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
        assert not any(i.severity == "critical" for i in report.issues)

    def test_auto_validate_retry_ok(self) -> None:
        r = _result(retry_count=0, timeout_status=None)
        report = auto_validate([r])
        assert not any(i.category == "retry" for i in report.issues)

    def test_auto_validate_invalid_timeout_status(self) -> None:
        r = _result(retry_count=0, timeout_status="unknown")
        report = auto_validate([r])
        assert any(i.category == "timeout" for i in report.issues)
