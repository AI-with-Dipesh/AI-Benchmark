from __future__ import annotations

import logging
import warnings
from typing import Any, TypeVar

from aibenchmark.app.models import PluginCategory
from aibenchmark.app.plugin.manager import PluginManager

T = TypeVar("T")
logger = logging.getLogger(__name__)

CURRENT_PLUGIN_API_VERSION = "1.0"


class PluginCompatibilityWarning(Warning):
    """Raised when a plugin declares an incompatible API version."""


def get_manager() -> PluginManager:
    if hasattr(get_manager, "_instance"):
        return get_manager._instance  # type: ignore[no-any-return, attr-defined]
    get_manager._instance = PluginManager()  # type: ignore[attr-defined]
    get_manager._instance.discover()  # type: ignore[attr-defined]
    return get_manager._instance  # type: ignore[no-any-return, attr-defined]


def _validate_plugin_metadata(cls: type[T]) -> None:
    """Validate a plugin class has required metadata attributes."""
    api_version = getattr(cls, "plugin_api_version", None)
    if api_version is None:
        warnings.warn(
            f"Plugin '{getattr(cls, 'plugin_name', cls.__name__)}' does not declare plugin_api_version; "
            f"assuming compatibility with {CURRENT_PLUGIN_API_VERSION}.",
            PluginCompatibilityWarning,
            stacklevel=3,
        )
        return
    if not isinstance(api_version, str):
        warnings.warn(
            f"Plugin '{getattr(cls, 'plugin_name', cls.__name__)}' has non-string plugin_api_version: {api_version!r}.",
            PluginCompatibilityWarning,
            stacklevel=3,
        )
        return
    major = api_version.split(".")[0]
    current_major = CURRENT_PLUGIN_API_VERSION.split(".")[0]
    if major != current_major:
        warnings.warn(
            f"Plugin '{getattr(cls, 'plugin_name', cls.__name__)}' declares plugin_api_version={api_version!r}; "
            f"current API version is {CURRENT_PLUGIN_API_VERSION}. Incompatibility may occur.",
            PluginCompatibilityWarning,
            stacklevel=3,
        )


def validate_all_plugins() -> list[dict[str, Any]]:
    mgr = get_manager()
    results = []
    for category in PluginCategory:
        for name in mgr.list_names(category):
            cls = mgr.get(category, name)
            if cls is None:
                continue
            issues: list[str] = []
            api_version = getattr(cls, "plugin_api_version", None)
            if api_version is None:
                issues.append("Missing plugin_api_version")
            elif not isinstance(api_version, str):
                issues.append(f"plugin_api_version must be a string, got {type(api_version).__name__}")
            elif api_version.split(".")[0] != CURRENT_PLUGIN_API_VERSION.split(".")[0]:
                issues.append(f"Incompatible API version: {api_version}")
            results.append({
                "name": name,
                "category": category.value,
                "plugin_api_version": api_version,
                "valid": not issues,
                "issues": issues,
            })
    return results


def register(category: PluginCategory, name: str | None = None) -> Any:
    def decorator(cls: type[T]) -> type[T]:
        cls.plugin_name = cls.plugin_name or name or cls.__name__ # type: ignore[attr-defined]
        cls.plugin_category = category.value # type: ignore[attr-defined]
        _validate_plugin_metadata(cls)
        mgr = get_manager()
        mgr.register(category, cls.plugin_name, cls) # type: ignore[attr-defined,arg-type]
        return cls
    return decorator
