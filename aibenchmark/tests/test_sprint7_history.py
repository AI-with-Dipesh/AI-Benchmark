from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from aibenchmark.app.history import init_db, recent_category_performance, recent_runs, save_run
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score


def _make_result(provider: str, model: str, benchmark: str, normalized: float) -> BenchmarkResult:
    return BenchmarkResult(
        provider=ProviderType(provider),
        model=model,
        scores=[Score(benchmark=BenchmarkName(benchmark), raw=normalized, normalized=normalized, weight=1.0)],
    )


def test_recent_runs_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    save_run([_make_result("ollama", "llama3", "coding", 0.8)], details={"source": "test"}, db_path=db)
    save_run([_make_result("openrouter", "gpt-4", "coding", 0.9)], details={"source": "test"}, db_path=db)
    runs = recent_runs(db_path=db, limit=2)
    assert len(runs) == 2
    assert runs[0]["provider"] == "openrouter"
    assert runs[1]["provider"] == "ollama"


def test_recent_category_performance_filters_by_benchmark(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    save_run([_make_result("ollama", "llama3", "coding", 0.8)], details={"source": "test"}, db_path=db)
    save_run([_make_result("ollama", "llama3", "reasoning", 0.6)], details={"source": "test"}, db_path=db)
    stats = recent_category_performance(db_path=db, benchmark_name="coding", limit=10)
    assert "ollama:llama3" in stats
    assert stats["ollama:llama3"]["normalized"] == pytest.approx(0.8)


def test_recent_category_performance_empty_history(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    stats = recent_category_performance(db_path=db, benchmark_name="coding", limit=10)
    assert stats == {}


def test_recent_category_performance_limits(tmp_path: Path) -> None:
    db = tmp_path / "history.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    conn.close()
    for i in range(5):
        save_run([_make_result("ollama", "llama3", "coding", 0.5 + i * 0.1)], details={"source": "test"}, db_path=db)
    stats = recent_category_performance(db_path=db, benchmark_name="coding", limit=3)
    assert len(stats) == 1
    # Should still return one key; limitation is GROUP BY provider/model aggregation
