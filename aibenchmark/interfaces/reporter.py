from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from aibenchmark.app.models import BenchmarkResult


class BaseReporter(ABC):
    plugin_name: str = ""
    plugin_category: str = "reporter"

    @abstractmethod
    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: Any) -> None: ...
