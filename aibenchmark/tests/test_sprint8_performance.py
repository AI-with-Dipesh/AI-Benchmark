"""Regression benchmarks for Sprint 8 performance changes."""

from __future__ import annotations

import time

import pytest

from aibenchmark.app.memory_profiler import MemoryProfiler
from aibenchmark.app.parallel_executor import ParallelExecutor
from aibenchmark.app.profiling import ProfileSession, profile_function


def test_parallel_executor_map_preserves_order() -> None:
    """AD-69: ParallelExecutor.map must remain deterministic."""
    executor = ParallelExecutor(max_workers=2)

    def job(i: int) -> int:
        time.sleep(0.005)
        return i * 10

    inputs = list(range(8))
    results = executor.map(job, inputs)
    assert results == [i * 10 for i in inputs]


def test_parallel_executor_map_swallows_exceptions() -> None:
    """Failing jobs should return None while others succeed."""
    executor = ParallelExecutor(max_workers=2)

    def job(v: Any) -> Any:
        if v == 2:
            raise RuntimeError("boom")
        return v

    results = executor.map(job, list(range(5)))
    assert results == [0, 1, None, 3, 4]


def test_parallel_executor_scales_with_workers() -> None:
    """With more workers, parallelism should reduce wall time for CPU-free work."""
    executor = ParallelExecutor(max_workers=4)

    def job(v: Any) -> Any:
        time.sleep(0.02 * v)
        return v

    inputs = [0, 1, 2, 3]
    start = time.perf_counter()
    results = executor.map(job, inputs)
    elapsed = time.perf_counter() - start
    assert results == inputs
    # The chain is 0+1+2+3 = 6 * 0.02 = 120ms; with 4 workers it should be < 80ms
    assert elapsed < 0.08


def test_profile_session_produces_summary() -> None:
    with ProfileSession("test") as sesh:
        sum(range(1000000))
    summary = sesh.summary(sort="tottime", top_n=5)
    assert "tottime" in summary or "cpu" in summary.lower() or "function" in summary.lower()


def test_profile_function_wraps_callable() -> None:
    result, summary = profile_function(lambda: sum(range(1000)), label="lambda")
    assert result == 499500
    assert isinstance(summary, str)
    assert len(summary) > 0


def test_memory_profiler_samples_rss() -> None:
    profiler = MemoryProfiler(enabled=True)
    profiler.start()
    profiler.snapshot("before")
    buf = bytearray(1024 * 1024)  # allocate 1 MB
    profiler.snapshot("after")
    profiler.record_rss()
    stats = profiler.stop()
    assert stats["tracemalloc_snapshots"] >= 2
    assert stats["peak_rss_mb"] > 0
    assert stats["mean_rss_mb"] > 0
    del buf


def test_measure_memory_decorator_returns_stats() -> None:
    from aibenchmark.app.memory_profiler import measure_memory

    def work() -> int:
        return sum(range(1000))

    result, stats = measure_memory(work, label="work")
    assert result == 499500
    assert stats["tracemalloc_snapshots"] >= 1
    assert stats["peak_rss_mb"] >= 0.0


__all__ = [
    "test_parallel_executor_map_preserves_order",
    "test_parallel_executor_map_swallows_exceptions",
    "test_parallel_executor_scales_with_workers",
    "test_profile_session_produces_summary",
    "test_profile_function_wraps_callable",
    "test_memory_profiler_samples_rss",
    "test_measure_memory_decorator_returns_stats",
]
