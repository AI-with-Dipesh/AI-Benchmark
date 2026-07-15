"""Integration test for external plugin registration, validation, and execution."""
from __future__ import annotations

import importlib.util
import warnings
from pathlib import Path

import pytest

from aibenchmark.app.models import PluginCategory
from aibenchmark.app.plugin.registry import (
    CURRENT_PLUGIN_API_VERSION,
    PluginCompatibilityWarning,
    _validate_plugin_metadata,
    get_manager,
)


EXTERNAL_PLUGIN_CODE = '''
"""Minimal external plugin for integration testing."""


class ExternalTestProvider:
    plugin_name = "external_test"
    plugin_api_version = "1.0"
    plugin_category = "provider"

    def __init__(self):
        self.name = ExternalTestProvider.plugin_name

    def validate(self):
        return True

    def execute(self, payload):
        return {"provider": self.name, "result": payload}
'''


def _load_external_plugin(tmp_path: Path):
    plugin_file = tmp_path / "external_plugin.py"
    plugin_file.write_text(EXTERNAL_PLUGIN_CODE, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("external_plugin", plugin_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_external_plugin_metadata_validation(tmp_path):
    module = _load_external_plugin(tmp_path)
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _validate_plugin_metadata(module.ExternalTestProvider)
    assert not any(issubclass(w.category, PluginCompatibilityWarning) for w in caught)


def test_external_plugin_registration_and_discovery(tmp_path):
    module = _load_external_plugin(tmp_path)

    manager = get_manager()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        manager.register(PluginCategory.PROVIDER, "external_test", module.ExternalTestProvider)

    registered = [cls for name, cls in manager.providers.items() if name == "external_test"]
    assert len(registered) == 1

    warnings_list = [str(w.message) for w in caught]
    assert not any("does not declare plugin_api_version" in msg for msg in warnings_list)


def test_external_plugin_compatibility_warning_for_incompatible_version(tmp_path):
    incompatible_code = EXTERNAL_PLUGIN_CODE.replace('plugin_api_version = "1.0"', 'plugin_api_version = "2.0"')
    plugin_file = tmp_path / "incompatible_plugin.py"
    plugin_file.write_text(incompatible_code, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("incompatible_plugin", plugin_file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        _validate_plugin_metadata(module.ExternalTestProvider)
    assert any(issubclass(w.category, PluginCompatibilityWarning) for w in caught)


def test_external_plugin_execution(tmp_path: Path):
    module = _load_external_plugin(tmp_path)
    provider = module.ExternalTestProvider()
    assert provider.validate() is True
    result = provider.execute({"task": "test"})
    assert result["provider"] == "external_test"
    assert result["result"] == {"task": "test"}
