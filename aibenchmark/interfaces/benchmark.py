from abc import ABC, abstractmethod
from typing import Any

from aibenchmark.app.models import BenchmarkResult, ResponseObject


class BaseBenchmark(ABC):
    plugin_name: str = ""
    plugin_category: str = "benchmark"

    def __init__(self, weight: float = 1.0) -> None:
        self.weight = weight

    @abstractmethod
    def run(self, response: ResponseObject, **kwargs: Any) -> BenchmarkResult: ...
