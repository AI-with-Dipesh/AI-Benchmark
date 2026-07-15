"""Memory usage profiling helpers."""

from __future__ import annotations

import logging
import os
import statistics
import time
import tracemalloc
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class MemoryProfiler:
    """Lightweight memory profiler for peak RSS and tracemalloc snapshots."""

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._tracemalloc_started = False
        self._snapshots: list[tracemalloc.Snapshot] = []
        self._rss_samples: list[float] = []

    def start(self) -> None:
        if not self.enabled:
            return
        if not tracemalloc.is_tracing():
            tracemalloc.start(5)
            self._tracemalloc_started = True

    def snapshot(self, label: str = "") -> None:
        if not self.enabled:
            return
        try:
            snap = tracemalloc.take_snapshot()
            self._snapshots.append(snap)
        except Exception as exc:  # pragma: no cover - tracemalloc edge cases
            logger.debug("tracemalloc snapshot failed at %s: %s", label, exc)

    def sample_rss(self) -> float:
        """Return current RSS in MB using /proc/self/status when available."""
        try:
            path = "/proc/self/status"
            if Path(path).exists():
                rss_kb = 0.0
                with open(path, "r") as fh:
                    for line in fh:
                        if line.startswith("VmRSS:"):
                            rss_kb = float(line.split()[1])
                            break
                return rss_kb / 1024.0
        except Exception as exc:
            logger.debug("Failed to read RSS: %s", exc)
        return 0.0

    def record_rss(self) -> None:
        rss = self.sample_rss()
        if rss:
            self._rss_samples.append(rss)

    def stop(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "peak_rss_mb": 0.0,
            "mean_rss_mb": 0.0,
            "max_tracemalloc_kb": 0.0,
            "tracemalloc_snapshots": len(self._snapshots),
        }
        if self._rss_samples:
            result["peak_rss_mb"] = max(self._rss_samples)
            result["mean_rss_mb"] = statistics.mean(self._rss_samples)
        if self._snapshots and self._tracemalloc_started:
            try:
                top = self._snapshots[-1].statistics("lineno")
                if top:
                    result["max_tracemalloc_kb"] = top[0].size / 1024.0
            except Exception as exc:
                logger.debug("tracemalloc statistics failed: %s", exc)
        if self._tracemalloc_started and tracemalloc.is_tracing():
            try:
                tracemalloc.stop()
            except Exception:
                pass
            self._tracemalloc_started = False
        return result


def measure_memory(func: Any, label: str | None = None) -> tuple[Any, dict[str, Any]]:
    """Run a function call while sampling RSS and return (result, stats)."""
    profiler = MemoryProfiler()
    profiler.start()
    profiler.record_rss()
    try:
        result = func()
    finally:
        profiler.snapshot(label or func.__name__)
        profiler.record_rss()
    stats = profiler.stop()
    return result, stats


__all__ = ["MemoryProfiler", "measure_memory"]
