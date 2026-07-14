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
            futures = {executor.submit(func, *args): idx for idx, args in enumerate(jobs)}
            for future in as_completed(futures):
                idx = futures[future]
                try:
                    result = future.result()
                except Exception as exc:
                    logger.debug("Parallel job %d failed: %s", idx, exc)
                    result = None
                results.append((idx, result))
        results.sort(key=lambda item: item[0])
        return [r for _, r in results]
