from __future__ import annotations

from pathlib import Path

import pytest

from aibenchmark.app.analytics import (
    build_comparison,
    build_leaderboard,
    build_team,
    build_trends,
    recommend,
    _reliability_score,
    best_value,
    most_stable,
    fastest,
    highest_quality,
)
from aibenchmark.app.history import load_latest, save_run
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score
from aibenchmark.plugins.reporters.analytics import (
    generate_compare,
    generate_leaderboard,
    generate_recommendations,
    generate_team,
    generate_trends,
)


def _make_result(provider: str, model: str, overall: float, scores: dict[str, float], latency_ms: float | None = None, reliability: float | None = None, timestamp: str | None = None) -> BenchmarkResult:
    meta: dict[str, Any] = {"latency_ms": latency_ms}
    if timestamp:
        meta["timestamp"] = timestamp
    return BenchmarkResult(
        model=model,
        provider=ProviderType(provider),
        scores=[Score(benchmark=BenchmarkName(cat), raw=val, normalized=val, weight=1.0) for cat, val in scores.items()],
        overall=overall,
        metadata=meta,
        details={"validation_summary": reliability} if reliability is not None else {},
    )


def test_build_trends_skips_malformed_key(tmp_path: Path) -> None:
    results = [
        _make_result("openai", "gpt", 0.8, {"coding": 0.8}, timestamp="2026-01-01T00:00:00+00:00"),
    ]
    db = tmp_path / "history.db"
    save_run(results, db_path=db)
    # Inject malformed key by directly modifying DB
    import sqlite3
    conn = sqlite3.connect(db)
    conn.execute("UPDATE benchmark_scores SET benchmark='bad:key:extra' WHERE run_id=1")
    conn.commit()
    conn.close()
    loaded = load_latest(1, db_path=db)
    trends = build_trends(loaded)
    assert "openai:gpt" in trends or trends == {}


def test_build_trends_single_run_no_trend() -> None:
    results = [_make_result("openai", "gpt", 0.8, {"coding": 0.8})]
    assert build_trends([results]) == {}


def test_recommend_trade_offs_populated() -> None:
    results = [
        _make_result("ollama", "a", 0.9, {"coding": 0.95}, latency_ms=50),
        _make_result("openai", "b", 0.8, {"coding": 0.8}, latency_ms=120),
    ]
    recs = recommend(results)
    coding = next(r for r in recs if r.category == "coding")
    assert len(coding.trade_offs) == 1
    assert "a" in coding.trade_offs[0] or "b" in coding.trade_offs[0]


def test_build_team_trade_offs_populated() -> None:
    results = [
        _make_result("ollama", "a", 0.9, {"coding": 0.95}, latency_ms=50),
        _make_result("openai", "b", 0.8, {"coding": 0.8}, latency_ms=120),
    ]
    roles = build_team(results)
    main = next(r for r in roles if r.role == "Main")
    assert len(main.trade_offs) == 1


def test_build_comparison_new_and_removed() -> None:
    old = [_make_result("openai", "m", 0.7, {"coding": 0.7})]
    new = [_make_result("openai", "m", 0.8, {"coding": 0.8, "reasoning": 0.9})]
    deltas = build_comparison(new, old)
    assert deltas["coding"].trend == "improved"
    assert deltas["reasoning"].trend == "new"
    assert deltas.get("debugging", None) is None


def test_reliability_score_from_details() -> None:
    r = _make_result("openai", "m", 0.8, {"coding": 0.8}, reliability=0.95)
    assert _reliability_score(r) == 0.95


def test_reliability_score_from_scores() -> None:
    r = _make_result("openai", "m", 0.8, {"coding": 0.8, "reliability": 0.9})
    assert _reliability_score(r) == 0.9


def test_best_value_returns_recommendation() -> None:
    results = [_make_result("openai", "m", 0.9, {"coding": 0.9}, latency_ms=100)]
    rec = best_value(results)
    assert rec is not None
    assert rec.category == "value"


def test_fastest_returns_result() -> None:
    results = [
        _make_result("openai", "a", 0.8, {"coding": 0.8}, latency_ms=200),
        _make_result("openai", "b", 0.8, {"coding": 0.8}, latency_ms=100),
    ]
    assert fastest(results).model == "b"


def test_highest_quality_returns_result() -> None:
    results = [
        _make_result("openai", "a", 0.9, {"coding": 0.9}),
        _make_result("openai", "b", 0.7, {"coding": 0.7}),
    ]
    assert highest_quality(results).model == "a"


def test_reporter_generate_contains_trade_offs(tmp_path: Path) -> None:
    results = [
        _make_result("ollama", "a", 0.9, {"coding": 0.95}, latency_ms=50),
        _make_result("openai", "b", 0.8, {"coding": 0.8}, latency_ms=120),
    ]
    p = tmp_path / "rec.md"
    generate_recommendations(results, p)
    assert "Trade-offs" in p.read_text()


def test_reporter_team_contains_trade_offs(tmp_path: Path) -> None:
    results = [
        _make_result("ollama", "a", 0.9, {"coding": 0.95}, latency_ms=50),
        _make_result("openai", "b", 0.8, {"coding": 0.8}, latency_ms=120),
    ]
    p = tmp_path / "team.md"
    generate_team(results, p)
    assert "Trade-offs" in p.read_text()


def test_load_latest_fresh_database(tmp_path: Path) -> None:
    db = tmp_path / "fresh.db"
    assert load_latest(1, db_path=db) == []


def test_compare_reporter_fallback(tmp_path: Path) -> None:
    results = [_make_result("openai", "m", 0.8, {"coding": 0.8})]
    p = tmp_path / "compare.md"
    generate_compare(results, p, db_path=tmp_path / "empty.db")
    assert "Category" in p.read_text() or "Need" in p.read_text()


def test_trends_reporter_fallback(tmp_path: Path) -> None:
    results = [_make_result("openai", "m", 0.8, {"coding": 0.8})]
    p = tmp_path / "trends.md"
    generate_trends(results, p, db_path=tmp_path / "empty.db")
    assert "Trends" in p.read_text() or "Need" in p.read_text()
