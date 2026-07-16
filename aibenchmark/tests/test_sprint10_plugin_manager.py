from __future__ import annotations



import pytest

from aibenchmark.app.models import PluginCategory
from aibenchmark.app.plugin.manager import PluginManager


@pytest.fixture()
def manager() -> PluginManager:
    mgr = PluginManager()
    cls = type("DummyPlugin", (), {"plugin_name": "dummy", "plugin_api_version": "1.0"})
    mgr.register(PluginCategory.BENCHMARK, "dummy", cls)
    return mgr


class _BadCat:
    value = "not_a_category"


class TestPluginManagerErrorPaths:
    def test_register_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            PluginManager().register(_BadCat(), "x", object)

    def test_get_unknown_category_returns_none(self):
        assert PluginManager().get(_BadCat(), "x") is None

    def test_unload_unknown_category_returns_false(self):
        assert PluginManager().unload(_BadCat(), "x") is False

    def test_set_enabled_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            PluginManager().set_enabled(_BadCat(), "x", True)

    def test_get_priority_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            PluginManager().get_priority(_BadCat(), "x")

    def test_set_priority_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            PluginManager().set_priority(_BadCat(), "x", 50)

    def test_add_alias_unknown_category_raises(self):
        with pytest.raises(ValueError, match="Unknown category"):
            PluginManager().add_alias(_BadCat(), "x", "alias")

    def test_unload_missing_name_returns_false(self, manager):
        assert manager.unload(PluginCategory.BENCHMARK, "missing") is False

    def test_set_enabled_missing_name_raises(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.set_enabled(PluginCategory.BENCHMARK, "missing", True)

    def test_get_priority_missing_name_raises(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.get_priority(PluginCategory.BENCHMARK, "missing")

    def test_set_priority_missing_name_raises(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.set_priority(PluginCategory.BENCHMARK, "missing", 50)

    def test_add_alias_missing_name_raises(self, manager):
        with pytest.raises(ValueError, match="not found"):
            manager.add_alias(PluginCategory.BENCHMARK, "missing", "alias")
