from __future__ import annotations

from pathlib import Path
import pytest

from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.models import BenchmarkName, PluginCategory, ProviderType


class FakeProvider:
    provider_type = ProviderType.OLLAMA

    def __init__(self, api_key: str, base_url: str = "", **kwargs):
        self.api_key = api_key
        self.base_url = base_url

    def chat(self, model: str, messages: list[dict]):
        from aibenchmark.app.models import ResponseObject
        return ResponseObject(
            provider=self.provider_type,
            model=model,
            content="def foo(): pass",
            latency_ms=200.0,
            tokens_in=10,
            tokens_out=15,
        )


def test_end_to_end_mocked(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("OLLAMA_API_KEY", "fake")
    engine = BenchEngine()
    engine.plugins.register(PluginCategory.PROVIDER, "ollama", FakeProvider)

    result = engine.run_benchmark("ollama", "fake-model", BenchmarkName.LATENCY, [{"role": "user", "content": "hi"}])
    assert result.overall >= 0.0
    assert result.model == "fake-model"
    assert len(result.scores) == 1
    assert result.metadata.get("timestamp")

    produced = engine.generate_reports([result], tmp_path)
    assert (tmp_path / "results.json").exists()
