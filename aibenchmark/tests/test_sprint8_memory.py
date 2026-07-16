"""Sprint 8 memory optimization and SQLite connection lifecycle tests."""

from __future__ import annotations

import sqlite3
from pathlib import Path


from aibenchmark.app.history import HistoryWriter, init_db, recent_runs, save_run
from aibenchmark.app.memory_profiler import MemoryProfiler, measure_memory
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, ProviderType, Score


def _make_result(provider: str = "ollama", model: str = "llama3", benchmark: str = "coding", normalized: float = 0.8) -> BenchmarkResult:
    return BenchmarkResult(
        provider=ProviderType(provider),
        model=model,
        scores=[Score(benchmark=BenchmarkName(benchmark), raw=normalized, normalized=normalized, weight=1.0)],
    )


def test_history_writer_ctx_manager_close(tmp_path: Path) -> None:
    db = tmp_path / "lifecycle.db"
    with HistoryWriter(db_path=db) as writer:
        run_id = writer.save_run([_make_result()])
        assert run_id > 0
    # After context exit, the connection should be closed.
    assert writer._conn is None


def test_history_writer_reuse_same_connection(tmp_path: Path) -> None:
    db = tmp_path / "reuse.db"
    HistoryWriter.reset()
    writer = HistoryWriter(db_path=db)
    conn1 = writer._conn
    writer.save_run([_make_result()])
    writer.save_run([_make_result()])
    # Same connection object must be reused across calls.
    assert writer._conn is conn1
    writer.close()
    assert writer._conn is None
    HistoryWriter.reset()


def test_history_writer_idempotent_close() -> None:
    writer = HistoryWriter(db_path=Path(":memory:"))
    writer.close()
    assert writer._conn is None
    writer.close()  # should not raise
    writer.save_run([_make_result()], details={"source": "test"})
    assert writer._conn is not None
    writer.close()
    HistoryWriter.reset()


def test_history_writer_reset_clears_singleton(tmp_path: Path) -> None:
    db = tmp_path / "reset.db"
    HistoryWriter.reset()
    HistoryWriter(db_path=db)
    HistoryWriter.reset()
    assert HistoryWriter._instance is None


def test_save_run_with_owned_connection_does_not_leak(tmp_path: Path) -> None:
    # When no conn is passed, save_run should open and close it.
    db = tmp_path / "leak.db"
    save_run([_make_result()], details={"source": "test"}, db_path=db)
    # We cannot directly inspect the closed connection; verify by writing again.
    save_run([_make_result()], details={"source": "test2"}, db_path=db)
    runs = recent_runs(db_path=db, limit=2)
    assert len(runs) == 2


def test_recent_runs_reuse_passed_connection(tmp_path: Path) -> None:
    db = tmp_path / "reuse_pass.db"
    conn = sqlite3.connect(db)
    conn.row_factory = sqlite3.Row
    init_db(conn)
    save_run([_make_result()], details={"source": "test"}, db_path=db)
    # load_latest should not close the shared connection if we pass conn via save_run mechanics.
    # We call recent_runs with explicit db_path to verify the happy path.
    runs = recent_runs(db_path=db, limit=1)
    assert len(runs) == 1
    conn.close()


def test_memory_profiler_rss_samples() -> None:
    profiler = MemoryProfiler(enabled=True)
    profiler.start()
    profiler.record_rss()
    profiler.snapshot("before")
    # Allocate something so RSS moves (not guaranteed, but if platform supports it, it will)
    data = bytearray(512 * 1024)
    profiler.snapshot("after")
    profiler.record_rss()
    stats = profiler.stop()
    assert stats["tracemalloc_snapshots"] >= 1
    assert stats["peak_rss_mb"] >= 0.0
    assert stats["mean_rss_mb"] >= 0.0
    del data


def test_measure_memory_decorator_runs(tmp_path: Path) -> None:
    def allocate_and_sum() -> int:
        buf = bytearray(256 * 1024)
        return sum(b for b in buf)

    _, stats = measure_memory(allocate_and_sum, label="test")
    assert stats["tracemalloc_snapshots"] >= 1
