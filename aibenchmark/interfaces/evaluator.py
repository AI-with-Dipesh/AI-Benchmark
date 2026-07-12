from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from aibenchmark.app.models import BenchmarkResult, Score


class BaseEvaluator(ABC):
    plugin_name: str = ""
    plugin_category: str = "evaluator"

    @abstractmethod
    def evaluate(self, result: BenchmarkResult, **kwargs: Any) -> Score | None: ...
