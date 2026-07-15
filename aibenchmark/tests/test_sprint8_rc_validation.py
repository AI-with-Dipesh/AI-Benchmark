from __future__ import annotations

import pytest

from aibenchmark.app.models import BenchmarkResult, ProviderType, Score
from aibenchmark.app.rc_validation import (
    check_metadata_bounds,
    check_overall_bounds,
    check_scores_bounds,
    validate_rc_bounds,
)


def _make_result(overall=0.8, scores=None, **kwargs):
    if scores is None:
        scores = [Score(benchmark="coding", raw=0.8, normalized=0.8, weight=1.0, weighted=0.8)]
    return BenchmarkResult(
        model="test-model",
        provider=ProviderType.OLLAMA,
        scores=scores,
        overall=overall,
        metadata={},
        **kwargs,
    )


# Overall bounds
def test_overall_in_bounds_valid():
    r = _make_result(overall=0.5)
    report = check_overall_bounds(r)
    assert report.valid is True
    assert report.issues == []


def test_overall_below_zero_fails():
    r = _make_result(overall=-0.1)
    report = check_overall_bounds(r)
    assert report.valid is False
    assert any(i.category == "bounds" for i in report.issues)


def test_overall_above_one_fails():
    r = _make_result(overall=1.1)
    report = check_overall_bounds(r)
    assert report.valid is False


# Score bounds
def test_scores_in_bounds_valid():
    scores = [Score(benchmark="coding", raw=0.5, normalized=0.5, weight=1.0, weighted=0.5)]
    r = _make_result(scores=scores)
    report = check_scores_bounds(r)
    assert report.valid is True


def test_raw_below_zero_fails():
    scores = [Score(benchmark="coding", raw=-0.1, normalized=0.0, weight=1.0, weighted=0.0)]
    r = _make_result(scores=scores)
    report = check_scores_bounds(r)
    assert report.valid is False
    assert any("raw score" in i.message for i in report.issues)


def test_raw_above_one_fails():
    scores = [Score(benchmark="coding", raw=1.5, normalized=0.0, weight=1.0, weighted=0.0)]
    r = _make_result(scores=scores)
    report = check_scores_bounds(r)
    assert report.valid is False


def test_zero_weight_fails():
    scores = [Score(benchmark="coding", raw=0.5, normalized=0.5, weight=0.0, weighted=0.0)]
    r = _make_result(scores=scores)
    report = check_scores_bounds(r)
    assert report.valid is False
    assert any("weight" in i.message for i in report.issues)


# Metadata bounds
def test_metadata_in_bounds_valid():
    r = _make_result(retry_count=2, estimated_cost=0.01, temperature=0.5, top_p=0.9)
    report = check_metadata_bounds(r)
    assert report.valid is True


def test_negative_retry_count_fails():
    r = _make_result(retry_count=-1)
    report = check_metadata_bounds(r)
    assert report.valid is False
    assert any("retry_count" in i.message for i in report.issues)


def test_negative_estimated_cost_fails():
    r = _make_result(estimated_cost=-0.01)
    report = check_metadata_bounds(r)
    assert report.valid is False
    assert any("estimated_cost" in i.message for i in report.issues)


def test_temperature_out_of_bounds_fails():
    r = _make_result(temperature=3.0)
    report = check_metadata_bounds(r)
    assert report.valid is False
    assert any("temperature" in i.message for i in report.issues)


def test_top_p_out_of_bounds_fails():
    r = _make_result(top_p=1.5)
    report = check_metadata_bounds(r)
    assert report.valid is False
    assert any("top_p" in i.message for i in report.issues)


# validate_rc_bounds aggregate
def test_validate_rc_bounds_critical_fails():
    r = _make_result(overall=1.5)
    report = validate_rc_bounds(r)
    assert report.valid is False
    assert any(i.severity == "critical" for i in report.issues)
