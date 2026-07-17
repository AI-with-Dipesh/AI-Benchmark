from __future__ import annotations

import logging
from importlib.metadata import entry_points

from aibenchmark.app.models import PluginCategory

logger = logging.getLogger(__name__)


def _normalize_category(category: PluginCategory | str) -> PluginCategory:
    if isinstance(category, PluginCategory):
        return category
    if isinstance(category, str):
        value = category.strip().lower()
        try:
            return PluginCategory(value)
        except ValueError:
            valid = {c.value for c in PluginCategory}
            raise ValueError(
                f"Unknown plugin category '{category}'. Valid: {sorted(valid)}"
            ) from None
    # Backward-compatible duck typing for objects with a .value attribute
    value = getattr(category, "value", None)
    if value is not None:
        for cat in PluginCategory:
            if str(cat.value).lower() == str(value).strip().lower():
                return cat
    valid = {c.value for c in PluginCategory}
    raise ValueError(
        f"Unknown category: '{category}'. Valid: {sorted(valid)}"
    )


def _coerce_category(category: PluginCategory | str) -> PluginCategory | None:
    if isinstance(category, PluginCategory):
        return category
    if isinstance(category, str):
        value = category.strip().lower()
        try:
            return PluginCategory(value)
        except ValueError:
            return None
    value = getattr(category, "value", None)
    if value is not None:
        for cat in PluginCategory:
            if str(cat.value).lower() == str(value).strip().lower():
                return cat
    return None


class PluginManager:
    def __init__(self) -> None:
        self.providers: dict[str, type] = {}
        self.benchmarks: dict[str, type] = {}
        self.evaluators: dict[str, type] = {}
        self.reporters: dict[str, type] = {}
        self.strategies: dict[str, type] = {}

    def register(self, category: PluginCategory | str, name: str, cls: type) -> None:
        cat = _normalize_category(category)
        store_name = cat.value
        if store_name == "strategy":
            store_name = "strategies"
        else:
            store_name = f"{store_name}s"
        store = getattr(self, store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {cat}")
        if name in store:
            logger.debug("Plugin %s already registered in %s; overwriting", name, cat)
        store[name] = cls

    def get(self, category: PluginCategory | str, name: str) -> type | None:
        cat = _coerce_category(category)
        if cat is None:
            return None
        store_name = cat.value if cat.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            return None
        return store.get(name)  # type: ignore[no-any-return]

    def list_names(self, category: PluginCategory | str) -> list[str]:
        cat = _normalize_category(category)
        store_name = cat.value if cat.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, {})
        return list(store.keys())

    def unload(self, category: PluginCategory | str, name: str) -> bool:
        cat = _coerce_category(category)
        if cat is None:
            return False
        store_name = cat.value if cat.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            return False
        return store.pop(name, None) is not None

    def set_enabled(self, category: PluginCategory | str, name: str, enabled: bool) -> None:
        cat = _normalize_category(category)
        store_name = cat.value if cat.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {cat}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{cat.value} '{name}' not found")
        cls.plugin_enabled = enabled

    def get_priority(self, category: PluginCategory | str, name: str) -> int:
        cat = _normalize_category(category)
        store_name = cat.value if cat.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {cat}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{cat.value} '{name}' not found")
        return int(getattr(cls, "plugin_priority", 100))

    def set_priority(self, category: PluginCategory | str, name: str, priority: int) -> None:
        cat = _normalize_category(category)
        store_name = cat.value if cat.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {cat}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{cat.value} '{name}' not found")
        cls.plugin_priority = int(priority)

    def add_alias(self, category: PluginCategory | str, name: str, alias: str) -> None:
        cat = _normalize_category(category)
        store_name = cat.value if cat.value != "strategy" else "strategies"
        store = getattr(self, f"{store_name}s" if store_name != "strategies" else store_name, None)
        if store is None:
            raise ValueError(f"Unknown category: {cat}")
        cls = store.get(name)
        if cls is None:
            raise ValueError(f"{cat.value} '{name}' not found")
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
