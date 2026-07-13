from __future__ import annotations

import pytest

from aibenchmark.app.provider_registry import ProviderRegistry


class TestProviderRegistry:
    def test_list_providers_returns_registered(self) -> None:
        registry = ProviderRegistry()
        providers = registry.list_providers()
        assert "nvidia" in providers
        assert "ollama" in providers
        assert "openrouter" in providers
        assert "huggingface" in providers

    def test_get_plugin_returns_class(self) -> None:
        registry = ProviderRegistry()
        cls = registry.get_plugin("nvidia")
        assert cls is not None
        assert cls.plugin_name == "nvidia"

    def test_instantiate_returns_instance(self) -> None:
        registry = ProviderRegistry()
        instance = registry.instantiate("nvidia", api_key="fake", base_url="https://integrate.api.nvidia.com/v1")
        assert instance.plugin_name == "nvidia"
        assert instance.api_key == "fake"

    def test_capabilities_returns_caps(self) -> None:
        registry = ProviderRegistry()
        caps = registry.capabilities("openrouter")
        assert caps.chat is True
        assert caps.streaming is True
        assert caps.vision is True

    def test_health_returns_provider_health(self) -> None:
        registry = ProviderRegistry()
        h = registry.health("nvidia")
        assert h.provider_name == "nvidia"
        from aibenchmark.app.models import ProviderStatus
        assert h.status in (ProviderStatus.AVAILABLE, ProviderStatus.UNAVAILABLE, ProviderStatus.DEGRADED, ProviderStatus.UNKNOWN)

    def test_list_models_nvidia(self) -> None:
        registry = ProviderRegistry()
        models = registry.list_models("nvidia")
        assert isinstance(models, list)

    def test_validate_configuration_nvidia(self) -> None:
        registry = ProviderRegistry()
        result = registry.validate_configuration("nvidia")
        assert "valid" in result
        assert "issues" in result

    def test_load_provider_imports_module(self) -> None:
        cls = ProviderRegistry.load_provider("nvidia")
        assert cls.plugin_name == "nvidia"

    def test_load_provider_unknown_raises(self) -> None:
        with pytest.raises(ImportError):
            ProviderRegistry.load_provider("unknown_provider_xyz")

    def test_compare_providers_returns_dict(self) -> None:
        registry = ProviderRegistry()
        result = registry.compare_providers(["nvidia", "ollama"], {"nvidia": [], "ollama": []})
        assert "overall_ranking" in result
        assert result["overall_ranking"][0]["provider"] in ("nvidia", "ollama")
