from __future__ import annotations

import pytest

from aibenchmark.app.models import PluginCategory
from aibenchmark.app.plugin.registry import get_manager


def test_manager_lists_builtin_plugins():
    import aibenchmark.plugins  # noqa: F401 - trigger built-in registration
    mgr = get_manager()
    assert "nvidia" in mgr.list_names(PluginCategory.PROVIDER)
    assert "latency" in mgr.list_names(PluginCategory.BENCHMARK)
    assert "json" in mgr.list_names(PluginCategory.REPORTER)


def test_engine_happy_path():
    from aibenchmark.app.engine import BenchEngine
    engine = BenchEngine()
    assert engine.list_providers()
    assert engine.list_benchmarks()


def test_manager_register_invalid_category():
    from aibenchmark.app.plugin.manager import PluginManager
    mgr = PluginManager()
    # PluginCategory("invalid") raises ValueError at enum creation.
    with pytest.raises(ValueError):
        mgr.register(PluginCategory("invalid"), "x", int)
