from __future__ import annotations

import logging
from importlib.metadata import entry_points

from aibenchmark.app.models import PluginCategory

logger = logging.getLogger(__name__)


class PluginManager:
    def __init__(self) -> None:
        self.providers: dict[str, type] = {}
        self.benchmarks: dict[str, type] = {}
        self.evaluators: dict[str, type] = {}
        self.reporters: dict[str, type] = {}
        self.strategies: dict[str, type] = {}

    def register(self, category: PluginCategory, name: str, cls: type) -> None:
        store_name = category.value
        if store_name == "strategy":
            store_name = "strategies"
        else:
            store_name = f"{store_name}s"
        store = getattr(self, store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {category}")
        if name in store:
            logger.debug("Plugin %s already registered in %s; overwriting", name, category)
        store[name] = cls

    def get(self, category: PluginCategory, name: str) -> type | None:
        store_name = category.value if category.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            return None
        return store.get(name)  # type: ignore[no-any-return]

    def list_names(self, category: PluginCategory) -> list[str]:
        store_name = category.value if category.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, {})
        return list(store.keys())

    def unload(self, category: PluginCategory, name: str) -> bool:
        store_name = category.value if category.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            return False
        return store.pop(name, None) is not None

    def set_enabled(self, category: PluginCategory, name: str, enabled: bool) -> None:
        store_name = category.value if category.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {category}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{category.value} '{name}' not found")
        cls.plugin_enabled = enabled

    def get_priority(self, category: PluginCategory, name: str) -> int:
        store_name = category.value if category.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {category}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{category.value} '{name}' not found")
        return int(getattr(cls, "plugin_priority", 100))

    def set_priority(self, category: PluginCategory, name: str, priority: int) -> None:
        store_name = category.value if category.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {category}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{category.value} '{name}' not found")
        cls.plugin_priority = int(priority)

    def add_alias(self, category: PluginCategory, name: str, alias: str) -> None:
        store_name = category.value if category.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {category}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{category.value} '{name}' not found")
        aliases: list[str] = getattr(cls, "plugin_aliases", [])
        if alias not in aliases:
            aliases.append(alias)
        cls.plugin_aliases = aliases

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
