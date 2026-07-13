from __future__ import annotations

import os

import pytest

from aibenchmark.app.provider_registry import ProviderRegistry


pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not any([
        os.environ.get("NVIDIA_API_KEY"),
        os.environ.get("OPENROUTER_API_KEY"),
        os.environ.get("OLLAMA_API_KEY"),
    ]),
    reason="No provider API keys configured; skip integration tests",
)
class TestProviderIntegration:
    def setup_method(self) -> None:
        self.registry = ProviderRegistry()

    def _provider_available(self, name: str) -> bool:
        try:
            h = self.registry.health(name)
            return h.status.value != "unavailable"
        except Exception:
            return False

    @pytest.mark.integration
    def test_openrouter_health(self) -> None:
        if not self._provider_available("openrouter"):
            pytest.skip("OpenRouter not available")
        h = self.registry.health("openrouter")
        assert h.provider_name == "openrouter"

    @pytest.mark.integration
    def test_nvidia_health(self) -> None:
        if not self._provider_available("nvidia"):
            pytest.skip("NVIDIA not available")
        h = self.registry.health("nvidia")
        assert h.provider_name == "nvidia"

    @pytest.mark.integration
    def test_ollama_health(self) -> None:
        if not self._provider_available("ollama"):
            pytest.skip("Ollama not available")
        h = self.registry.health("ollama")
        assert h.provider_name == "ollama"

    @pytest.mark.integration
    def test_openrouter_metadata(self) -> None:
        if not self._provider_available("openrouter"):
            pytest.skip("OpenRouter not available")
        meta = self.registry.metadata("openrouter")
        assert meta["provider_name"] == "openrouter"

    @pytest.mark.integration
    def test_nvidia_models(self) -> None:
        if not self._provider_available("nvidia"):
            pytest.skip("NVIDIA not available")
        models = self.registry.list_models("nvidia")
        assert len(models) > 0

    @pytest.mark.integration
    def test_cross_provider_compare(self) -> None:
        available = [p for p in self.registry.list_providers() if self._provider_available(p)]
        if len(available) < 2:
            pytest.skip("Need >=2 providers for comparison")
        result = self.registry.compare_providers(available, {p: [] for p in available})
        assert len(result["overall_ranking"]) >= 2
