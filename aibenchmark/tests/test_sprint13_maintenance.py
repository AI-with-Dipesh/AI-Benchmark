from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import pytest

from aibenchmark.app.models import PluginCategory
from aibenchmark.app.plugin.manager import PluginManager
from aibenchmark.app.provider_cache import ModelCache


class TestPluginManagerTypeCoercion:
    """Sprint 13: PluginManager must accept PluginCategory enum and string inputs."""

    @pytest.fixture()
    def manager(self) -> PluginManager:
        mgr = PluginManager()
        cls = type("DummyPlugin", (), {"plugin_name": "dummy", "plugin_api_version": "1.0"})
        mgr.register(PluginCategory.BENCHMARK, "dummy", cls)
        return mgr

    def test_list_names_with_enum(self, manager: PluginManager) -> None:
        assert "dummy" in manager.list_names(PluginCategory.BENCHMARK)

    def test_list_names_with_string(self, manager: PluginManager) -> None:
        assert "dummy" in manager.list_names("benchmark")

    def test_list_names_with_mixed_case_string(self, manager: PluginManager) -> None:
        assert "dummy" in manager.list_names("Benchmark")

    def test_list_names_unknown_string_raises(self, manager: PluginManager) -> None:
        with pytest.raises(ValueError, match="Unknown plugin category"):
            manager.list_names("not_a_category")

    def test_get_with_string(self, manager: PluginManager) -> None:
        assert manager.get("benchmark", "dummy") is not None
        assert manager.get("Benchmark", "dummy") is not None

    def test_register_with_string(self) -> None:
        mgr = PluginManager()
        mgr.register("benchmark", "string_reg", type("P", (), {}))
        assert "string_reg" in mgr.list_names("benchmark")

    def test_unload_with_string(self, manager: PluginManager) -> None:
        assert manager.unload("benchmark", "dummy") is True
        assert manager.unload("benchmark", "dummy") is False

    def test_set_enabled_with_string(self, manager: PluginManager) -> None:
        manager.set_enabled("benchmark", "dummy", True)
        manager.set_enabled("benchmark", "dummy", False)

    def test_get_priority_with_string(self, manager: PluginManager) -> None:
        assert manager.get_priority("benchmark", "dummy") in (100, 0)

    def test_set_priority_with_string(self, manager: PluginManager) -> None:
        manager.set_priority("benchmark", "dummy", 50)
        assert manager.get_priority("benchmark", "dummy") == 50

    def test_add_alias_with_string(self, manager: PluginManager) -> None:
        manager.add_alias("benchmark", "dummy", "alias1")
        assert manager.get_priority("benchmark", "dummy") in (100, 0)


class TestModelCache:
    def test_set_and_get(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cache = ModelCache(path=tmp_path / "cache.json", ttl=3600)
        cache.set("provider_a", ["m1", "m2"])
        assert cache.get("provider_a") == ["m1", "m2"]

    def test_expiry_falls_back_to_none(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        cache = ModelCache(path=tmp_path / "cache.json", ttl=1)
        cache.set("provider_a", ["m1"])
        time.sleep(1.1)
        assert cache.get("provider_a") is None

    def test_missing_provider_returns_none(self, tmp_path: Path) -> None:
        cache = ModelCache(path=tmp_path / "cache.json", ttl=3600)
        assert cache.get("does_not_exist") is None

    def test_invalidate_single(self, tmp_path: Path) -> None:
        cache = ModelCache(path=tmp_path / "cache.json", ttl=3600)
        cache.set("provider_a", ["m1"])
        cache.invalidate("provider_a")
        assert cache.get("provider_a") is None

    def test_invalidate_all(self, tmp_path: Path) -> None:
        cache = ModelCache(path=tmp_path / "cache.json", ttl=3600)
        cache.set("a", ["m1"])
        cache.set("b", ["m2"])
        cache.invalidate()
        assert cache.get("a") is None
        assert cache.get("b") is None

    def test_stats(self, tmp_path: Path) -> None:
        cache = ModelCache(path=tmp_path / "cache.json", ttl=3600)
        cache.set("a", ["m1"])
        stats = cache.stats()
        assert stats["cached_providers"] == 1
        assert stats["path"] == str(tmp_path / "cache.json")

    def test_atomic_write(self, tmp_path: Path) -> None:
        cache = ModelCache(path=tmp_path / "cache.json", ttl=3600)
        cache.set("a", ["m1"])
        assert not (tmp_path / "cache.json.tmp").exists()
        data = json.loads((tmp_path / "cache.json").read_text())
        assert data["a"]["models"] == ["m1"]


class TestProviderRegistryCache:
    def test_list_models_falls_back_on_cache(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from aibenchmark.app.provider_registry import ProviderRegistry

        # Create a fake provider plugin that raises on list_models
        class FakeProvider:
            plugin_category = "provider"
            plugin_name = "fake"
            plugin_api_version = "1.0"

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def list_models(self) -> list[str]:
                raise RuntimeError("API unavailable")

        import aibenchmark.plugins  # noqa: F401
        from aibenchmark.app.plugin.registry import get_manager

        mgr = get_manager()
        mgr.register(PluginCategory.PROVIDER, "fake", FakeProvider)

        registry = ProviderRegistry(cache_path=str(tmp_path / "cache.json"))
        # Pre-populate cache
        registry.model_cache.set("fake", ["cached_model"])
        # list_models should fall back to cache
        assert registry.list_models("fake") == ["cached_model"]

    def test_list_models_updates_cache_on_success(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from aibenchmark.app.provider_registry import ProviderRegistry

        class FakeProvider:
            plugin_category = "provider"
            plugin_name = "fake2"
            plugin_api_version = "1.0"

            def __init__(self, *args: Any, **kwargs: Any) -> None:
                pass

            def list_models(self) -> list[str]:
                return ["live_model"]

        import aibenchmark.plugins  # noqa: F401
        from aibenchmark.app.plugin.registry import get_manager

        mgr = get_manager()
        mgr.register(PluginCategory.PROVIDER, "fake2", FakeProvider)

        registry = ProviderRegistry(cache_path=str(tmp_path / "cache2.json"))
        result = registry.list_models("fake2")
        assert result == ["live_model"]
        assert registry.model_cache.get("fake2") == ["live_model"]
