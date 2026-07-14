from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseStrategy(ABC):
    plugin_name: str = ""
    plugin_category: str = "strategy"

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]: ...
