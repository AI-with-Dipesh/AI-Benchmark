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


def test_manager_register_invalid_category() -> None:
    from aibenchmark.app.plugin.manager import PluginManager
    mgr = PluginManager()
    # PluginCategory("invalid") raises ValueError at enum creation.
    with pytest.raises(ValueError):
        mgr.register(PluginCategory("invalid"), "x", int)


class _DummyPlugin:
    plugin_enabled: bool = True
    plugin_priority: int = 100
    plugin_aliases: list[str] = []


class TestPluginManagerLifecycle:
    def test_unload_removes_provider(self) -> None:
        from aibenchmark.app.plugin.manager import PluginManager
        mgr = PluginManager()
        mgr.register(PluginCategory.PROVIDER, "testp", _DummyPlugin)
        assert mgr.get(PluginCategory.PROVIDER, "testp") is _DummyPlugin
        assert mgr.unload(PluginCategory.PROVIDER, "testp") is True
        assert mgr.get(PluginCategory.PROVIDER, "testp") is None

    def test_unload_returns_false_for_missing(self) -> None:
        from aibenchmark.app.plugin.manager import PluginManager
        mgr = PluginManager()
        assert mgr.unload(PluginCategory.PROVIDER, "missing") is False

    def test_set_enabled(self) -> None:
        from aibenchmark.app.plugin.manager import PluginManager
        mgr = PluginManager()
        mgr.register(PluginCategory.PROVIDER, "testp", _DummyPlugin)
        mgr.set_enabled(PluginCategory.PROVIDER, "testp", False)
        assert _DummyPlugin.plugin_enabled is False

    def test_set_enabled_missing_raises(self) -> None:
        from aibenchmark.app.plugin.manager import PluginManager
        mgr = PluginManager()
        with pytest.raises(ValueError):
            mgr.set_enabled(PluginCategory.PROVIDER, "missing", False)

    def test_get_priority_default(self) -> None:
        from aibenchmark.app.plugin.manager import PluginManager
        mgr = PluginManager()
        mgr.register(PluginCategory.PROVIDER, "testp", _DummyPlugin)
        assert mgr.get_priority(PluginCategory.PROVIDER, "testp") == 100

    def test_set_priority(self) -> None:
        from aibenchmark.app.plugin.manager import PluginManager
        mgr = PluginManager()
        mgr.register(PluginCategory.PROVIDER, "testp", _DummyPlugin)
        mgr.set_priority(PluginCategory.PROVIDER, "testp", 50)
        assert mgr.get_priority(PluginCategory.PROVIDER, "testp") == 50

    def test_add_alias(self) -> None:
        from aibenchmark.app.plugin.manager import PluginManager
        mgr = PluginManager()
        mgr.register(PluginCategory.PROVIDER, "testp", _DummyPlugin)
        mgr.add_alias(PluginCategory.PROVIDER, "testp", "alias1")
        mgr.add_alias(PluginCategory.PROVIDER, "testp", "alias2")
        assert getattr(_DummyPlugin, "plugin_aliases", []) == ["alias1", "alias2"]
