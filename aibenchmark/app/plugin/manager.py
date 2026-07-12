from __future__ import annotations

import logging
from importlib.metadata import entry_points
from typing import Any

from aibenchmark.app.models import BenchmarkResult, PluginCategory

logger = logging.getLogger(__name__)


class PluginManager:
    def __init__(self) -> None:
        self.providers: dict[str, type] = {}
        self.benchmarks: dict[str, type] = {}
        self.evaluators: dict[str, type] = {}
        self.reporters: dict[str, type] = {}
        self.strategies: dict[str, type] = {}

    def register(self, category: PluginCategory, name: str, cls: type) -> None:
        store = getattr(self, category.value + "s", None)
        if store is None:
            raise ValueError(f"Unknown category: {category}")
        if name in store:
            logger.debug("Plugin %s already registered in %s; overwriting", name, category)
        store[name] = cls

    def get(self, category: PluginCategory, name: str) -> type | None:
        return getattr(self, category.value + "s", {}).get(name)

    def list_names(self, category: PluginCategory) -> list[str]:
        return list(getattr(self, category.value + "s", {}).keys())

    def discover(self) -> None:
        # Map entry point group name to plugin category
        group_map = {
            "aibenchmark.providers": PluginCategory.PROVIDER,
            "aibenchmark.benchmarks": PluginCategory.BENCHMARK,
            "aibenchmark.evaluators": PluginCategory.EVALUATOR,
            "aibenchmark.reporters": PluginCategory.REPORTER,
            "aibenchmark.strategies": PluginCategory.STRATEGY,
        }
        for group, category in group_map.items():
            try:
                for ep in entry_points().select(group=group):
                    try:
                        cls = ep.load()
                        self.register(category, ep.name, cls)
                    except Exception as exc:
                        logger.warning("Failed to load entry point %s: %s", ep.name, exc)
            except Exception as exc:
                logger.warning("Failed to load entry points for %s: %s", group, exc)
