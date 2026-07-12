from __future__ import annotations

import logging
from functools import wraps
from typing import TypeVar

from aibenchmark.app.models import PluginCategory
from aibenchmark.app.plugin.manager import PluginManager

T = TypeVar("T")
logger = logging.getLogger(__name__)


def get_manager() -> PluginManager:
    if hasattr(get_manager, "_instance"):
        return get_manager._instance # type: ignore[return-value]
    get_manager._instance = PluginManager() # type: ignore[attr-defined]
    get_manager._instance.discover() # type: ignore[attr-defined]
    return get_manager._instance # type: ignore[return-value]


def register(category: PluginCategory, name: str | None = None) -> Any:
    def decorator(cls: type[T]) -> type[T]:
        cls.plugin_name = cls.plugin_name or name or cls.__name__ # type: ignore[attr-defined]
        cls.plugin_category = category.value # type: ignore[attr-defined]
        mgr = get_manager()
        mgr.register(category, cls.plugin_name, cls) # type: ignore[attr-defined,arg-type]
        return cls
    return decorator
