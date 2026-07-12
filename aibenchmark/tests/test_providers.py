from __future__ import annotations

from unittest.mock import MagicMock
import pytest

from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.models import PluginCategory


class MockProvider:
    def __init__(self, api_key: str, base_url: str = "", **kwargs):
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, model: str, messages: list[dict]):
        from aibenchmark.app.models import ResponseObject, ProviderType
        return ResponseObject(
            provider=ProviderType.OLLAMA,
            model=model,
            content="hello",
            latency_ms=123.0,
            tokens_in=5,
            tokens_out=10,
        )


def test_engine_initializes_provider_with_api_key(monkeypatch):
    monkeypatch.setenv("OLLAMA_API_KEY", "fake-key")
    engine = BenchEngine()
    engine.plugins.register(PluginCategory.PROVIDER, "ollama", MockProvider)
    provider = engine._init_provider("ollama")
    assert provider.api_key == "fake-key"


def test_engine_raises_on_missing_api_key(monkeypatch):
    monkeypatch.delenv("OLLAMA_API_KEY", raising=False)
    engine = BenchEngine()
    with pytest.raises(ValueError, match="Missing API key"):
        engine._init_provider("ollama")