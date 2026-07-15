from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Callable, Sequence


logger = logging.getLogger(__name__)


class ParallelExecutor:
    def __init__(self, max_workers: int = 4) -> None:
        self.max_workers = max_workers

    def map(self, func: Callable[..., Any], *iterables: Sequence[Any]) -> list[Any]:
        jobs = list(zip(*iterables))
        results: list[Any] = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = executor.map(
                lambda args: _parallel_job(func, args), jobs, timeout=None
            )
            results = list(futures)
        return results


def _parallel_job(func: Callable[..., Any], args: tuple[Any, ...]) -> Any:
    try:
        return func(*args)
    except Exception as exc:
        logger.debug("Parallel job failed: %s", exc)
        return None
