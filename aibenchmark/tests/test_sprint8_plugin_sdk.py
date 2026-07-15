from __future__ import annotations

import warnings

import pytest

from aibenchmark.app.models import PluginCategory
from aibenchmark.app.plugin.registry import (
    CURRENT_PLUGIN_API_VERSION,
    PluginCompatibilityWarning,
    _validate_plugin_metadata,
    get_manager,
    validate_all_plugins,
)


class _FakePlugin:
    plugin_name: str = "fake"
    plugin_category: str = "provider"
    plugin_enabled: bool = True
    plugin_priority: int = 100
    plugin_aliases: list[str] = []


class _MissingApiVersion:
    plugin_name = "missing_api_version"
    plugin_category = "provider"
    plugin_enabled = True
    plugin_priority = 100
    plugin_aliases = []


class _BadApiVersion:
    plugin_name = "bad_api_version"
    plugin_category = "provider"
    plugin_enabled = True
    plugin_priority = 100
    plugin_aliases = []
    plugin_api_version = 123


class _IncompatibleApiVersion:
    plugin_name = "incompatible_api_version"
    plugin_category = "provider"
    plugin_enabled = True
    plugin_priority = 100
    plugin_aliases = []
    plugin_api_version = "2.0"


class _CompatibleApiVersion:
    plugin_name = "compatible_api_version"
    plugin_category = "provider"
    plugin_enabled = True
    plugin_priority = 100
    plugin_aliases = []
    plugin_api_version = "1.0"


def test_validate_missing_api_version_warns() -> None:
    with pytest.warns(PluginCompatibilityWarning, match="does not declare plugin_api_version"):
        _validate_plugin_metadata(_MissingApiVersion)


def test_validate_non_string_api_version_warns() -> None:
    with pytest.warns(PluginCompatibilityWarning, match="non-string plugin_api_version"):
        _validate_plugin_metadata(_BadApiVersion)


def test_validate_incompatible_api_version_warns() -> None:
    with pytest.warns(PluginCompatibilityWarning, match="Incompatibility"):
        _validate_plugin_metadata(_IncompatibleApiVersion)


def test_validate_compatible_api_version_silent() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        _validate_plugin_metadata(_CompatibleApiVersion)


def test_validate_fake_plugin_api_version_is_warned() -> None:
    with pytest.warns(PluginCompatibilityWarning, match="does not declare plugin_api_version"):
        _validate_plugin_metadata(_FakePlugin)


def test_validate_all_plugins_returns_results() -> None:
    import aibenchmark.plugins  # noqa: F401 - trigger built-in registration

    # Register some test plugins
    mgr = get_manager()
    mgr.register(PluginCategory.PROVIDER, "compatible_api_version", _CompatibleApiVersion)
    mgr.register(PluginCategory.PROVIDER, "missing_api_version", _MissingApiVersion)

    results = validate_all_plugins()
    names = {r["name"] for r in results}
    assert "compatible_api_version" in names
    assert "missing_api_version" in names

    missing = next(r for r in results if r["name"] == "missing_api_version")
    assert missing["valid"] is False
    assert "Missing plugin_api_version" in missing["issues"]

    compatible = next(r for r in results if r["name"] == "compatible_api_version")
    assert compatible["valid"] is True
    assert compatible["plugin_api_version"] == "1.0"


def test_current_plugin_api_version_is_string() -> None:
    assert isinstance(CURRENT_PLUGIN_API_VERSION, str)
    parts = CURRENT_PLUGIN_API_VERSION.split(".")
    assert len(parts) >= 1
