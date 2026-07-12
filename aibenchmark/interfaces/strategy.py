from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aibenchmark.app.models import BenchmarkResult


class BaseStrategy(ABC):
    plugin_name: str = ""
    plugin_category: str = "strategy"

    @abstractmethod
    def recommend(self, results: list[BenchmarkResult], **kwargs: Any) -> dict[str, Any]: ...
