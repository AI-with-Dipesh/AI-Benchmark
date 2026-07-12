from __future__ import annotations

import sqlite3
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from aibenchmark.app.analytics import (
    ComparisonDelta,
    LeaderboardEntry,
    Recommendation,
    TeamRole,
    TrendEntry,
    build_comparison,
    build_leaderboard,
    build_team,
    build_trends,
    recommend,
)
from aibenchmark.app.history import DB_PATH, init_db, load_latest, load_run, save_run
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score


def _make_result(provider: str, model: str, overall: float, scores: dict[str, float], latency_ms: float | None = None) -> BenchmarkResult:
    return BenchmarkResult(
        model=model,
        provider=ProviderType(provider),
        scores=[Score(benchmark=BenchmarkName(cat), raw=val, normalized=val, weight=1.0) for cat, val in scores.items()],
        overall=overall,
        metadata={"latency_ms": latency_ms, "timestamp": datetime.now(timezone.utc).isoformat()},
    )


def test_recommend_selects_best_per_category() -> None:
    results = [
        _make_result("ollama", "llama3", 0.8, {"coding": 0.95, "reasoning": 0.7}, latency_ms=50),
        _make_result("openrouter", "gpt", 0.78, {"coding": 0.8, "reasoning": 0.85}, latency_ms=120),
    ]
    recs = recommend(results)
    coding = next(r for r in recs if r.category == "coding")
    assert coding.model == "llama3"
    assert coding.confidence > 0


def test_recommend_confidence_label() -> None:
    results = [_make_result("ollama", "llama3", 0.9, {"general": 0.9}, latency_ms=50)]
    recs = recommend(results)
    assert recs[0].confidence_label in {"Low", "Medium", "High"}


def test_recommend_includes_reasons() -> None:
    results = [_make_result("ollama", "llama3", 0.9, {"general": 0.9}, latency_ms=50)]
    recs = recommend(results)
    assert recs[0].reasons


def test_build_team_has_required_roles() -> None:
    results = [
        _make_result("ollama", "llama3", 0.8, {"coding": 0.95, "debugging": 0.7, "reasoning": 0.75, "research": 0.8, "code_review": 0.85}, latency_ms=50),
    ]
    roles = build_team(results)
    role_names = {r.role for r in roles}
    expected = {"Main", "Coding", "Debugging", "Reasoning", "Research", "Review", "Fast", "Fallback"}
    assert expected.issubset(role_names)


def test_build_leaderboard_ordering() -> None:
    results = [
        _make_result("ollama", "a", 0.6, {"coding": 0.6}),
        _make_result("openrouter", "b", 0.9, {"coding": 0.9}),
    ]
    rows = build_leaderboard(results)
    assert rows[0].model == "b"
    assert rows[1].model == "a"


def test_build_comparison_trends() -> None:
    a = [_make_result("ollama", "a", 0.7, {"coding": 0.7})]
    b = [_make_result("ollama", "a", 0.8, {"coding": 0.8})]
    deltas = build_comparison(b, a)
    assert deltas["coding"].trend == "improved"


def test_build_trends_requires_multiple_runs() -> None:
    assert build_trends([]) == {}


def test_history_lifecycle(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    results = [_make_result("ollama", "llama3", 0.8, {"coding": 0.8})]
    run_id = save_run(results, details={"loop": 1}, db_path=db)
    loaded = load_run(run_id, db_path=db)
    assert len(loaded) == 1
    assert loaded[0].model == "llama3"
    assert loaded[0].overall == pytest.approx(0.8)
