"""cProfile-based profiling helpers for hot-path analysis."""

from __future__ import annotations

import cProfile
import io
import logging
import pstats
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class ProfileSession:
    """Collect cProfile data for a section of code and summarize hot paths."""

    def __init__(self, label: str) -> None:
        self.label = label
        self._profiler = cProfile.Profile()
        self._start_stats: dict[str, Any] | None = None

    def __enter__(self) -> ProfileSession:
        self._profiler.enable()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        self._profiler.disable()

    def dump(self, path: str | Path) -> None:
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self._profiler.dump_stats(str(path))

    def summary(self, sort: str = "cumulative", top_n: int = 20) -> str:
        stream = io.StringIO()
        stats = pstats.Stats(self._profiler, stream=stream)
        stats.sort_stats(sort)
        stats.print_stats(top_n)
        return stream.getvalue()


def profile_function(func: Any, label: str | None = None) -> tuple[Any, str]:
    """Profile a single function call and return (result, summary)."""
    sesh = ProfileSession(label or func.__name__)
    with sesh:
        result = func()
    return result, sesh.summary()


__all__ = ["ProfileSession", "profile_function"]
