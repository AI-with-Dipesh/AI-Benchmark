from __future__ import annotations

import os
import tempfile
from pathlib import Path
from importlib.metadata import EntryPoint

import pytest
from click.testing import CliRunner

from aibenchmark.app.config import ConfigError
from aibenchmark.app.models import BenchmarkName, PluginCategory, ProviderType
from aibenchmark.app.prompts import PromptLoader, PromptLoadError
from aibenchmark.app.plugin.manager import PluginManager
from aibenchmark.interfaces.provider import BaseProvider
from aibenchmark.cli import cli as cli_group


class DummyProvider(BaseProvider):
    provider_type = ProviderType.OLLAMA

    def connect(self) -> None:
        pass

    def list_models(self) -> list[str]:
        return []

    def chat(self, model: str, messages: list[dict[str, str]], **kwargs) -> "ResponseObject":
        from aibenchmark.app.models import ResponseObject
        return ResponseObject(provider=self.provider_type, model=model, content="", latency_ms=0.0)


class BrokenProvider(BaseProvider):
    provider_type = ProviderType.OLLAMA

    def connect(self) -> None:
        raise RuntimeError("boom")

    def list_models(self) -> list[str]:
        return []

    def chat(self, model: str, messages: list[dict[str, str]], **kwargs) -> "ResponseObject":
        from aibenchmark.app.models import ResponseObject
        return ResponseObject(provider=self.provider_type, model=model, content="", latency_ms=0.0)


def test_config_defaults_without_defaults_block(tmp_path: Path) -> None:
    (tmp_path / "providers.yaml").write_text("ollama:\n  api_key_env: OLLAMA_API_KEY\n")
    (tmp_path / "benchmark.yaml").write_text("weights:\n  coding: 25\ndefault_prompts: {}\n")
    from aibenchmark.app.config import AppConfig
    cfg = AppConfig(tmp_path)
    assert cfg.defaults() == {}
    assert cfg.weight(BenchmarkName.CODING) == 25.0
    assert cfg.prompt_path(BenchmarkName.CODING) is None


def test_config_prompt_path_outside_config_dir(tmp_path: Path) -> None:
    outside = tmp_path.parent / "outside"
    outside.mkdir(exist_ok=True)
    prompt_file = outside / "prompt.yaml"
    prompt_file.write_text("name: x\n")
    (tmp_path / "providers.yaml").write_text("defaults: {}\n")
    (tmp_path / "benchmark.yaml").write_text("default_prompts:\n  coding: ../outside/prompt.yaml\n")
    from aibenchmark.app.config import AppConfig
    cfg = AppConfig(tmp_path)
    resolved = cfg.prompt_path("coding")
    assert resolved is not None
    assert resolved.exists()


def test_engine_prompt_metadata_passed_to_benchmark(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "fake")
    from aibenchmark.app.engine import BenchEngine
    from aibenchmark.app.models import BenchmarkResult
    from aibenchmark.app.plugin.registry import get_manager

    engine = BenchEngine()
    captured: dict[str, dict[str, Any]] = {}

    def fake_run(response, prompt=None, **kwargs):
        captured["prompt"] = prompt
        return BenchmarkResult(
            model="fake-model",
            provider=ProviderType.OLLAMA,
            scores=[],
            details={"raw_score": 0.0, "normalized": 0.0},
            metadata={},
        )

    class FakeBenchmark:
        plugin_name = "fake"
        def run(self, response, prompt=None, **kwargs):
            return fake_run(response, prompt=prompt, **kwargs)

    monkeypatch.setattr(engine.plugins, "get", lambda category, name: None if category == PluginCategory.PROVIDER else FakeBenchmark)
    monkeypatch.setattr(engine, "_init_provider", lambda provider_name, **kwargs: type("FakeProvider", (), {"chat": staticmethod(lambda model, messages: type("Resp", (), {"provider": ProviderType.OLLAMA, "model": model, "content": "hi", "latency_ms": 1.0, "tokens_in": 1, "tokens_out": 1})())})())
    try:
        engine.run_benchmark("ollama", "fake-model", BenchmarkName.CODING, [{"role": "user", "content": "hi"}])
    except Exception:
        pass
    assert "prompt" in captured


def test_engine_unknown_provider_raises(monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_API_KEY", "fake")
    from aibenchmark.app.engine import BenchEngine
    engine = BenchEngine()
    with pytest.raises(ValueError):
        engine.run_benchmark("nope", "m", BenchmarkName.LATENCY, [{"role": "user", "content": "hi"}])


def test_prompt_loader_malformed_prompt_raises(tmp_path: Path) -> None:
    prompts = tmp_path / "prompts"
    prompts.mkdir()
    bad = prompts / "bad.yaml"
    bad.write_text("\t:\n")
    (tmp_path / "providers.yaml").write_text("defaults: {}\n")
    (tmp_path / "benchmark.yaml").write_text("default_prompts:\n  coding: prompts/bad.yaml\n")
    loader = PromptLoader(tmp_path)
    with pytest.raises(PromptLoadError):
        loader.load("coding")


def test_plugin_manager_discover_handles_broken_entry_point(monkeypatch) -> None:
    mgr = PluginManager()

    class FakeEntryPoints:
        def select(self, group: str):
            return [EntryPoint(name="broken", group="aibenchmark.benchmarks", value="nonexistent.module:X")]

    monkeypatch.setattr("aibenchmark.app.plugin.manager.entry_points", lambda: FakeEntryPoints())
    mgr.discover()


def test_base_provider_capability_defaults() -> None:
    provider = DummyProvider(api_key="x", base_url="")
    assert provider.supports_streaming() is False
    assert provider.supports_tools() is True
    assert provider.supports_json() is True
    assert provider.supports_context_length() is True
    meta = provider.metadata()
    assert meta["streaming"] is False
    assert meta["tools"] is True


def test_base_provider_health_check_returns_false() -> None:
    provider = BrokenProvider(api_key="x", base_url="")
    assert provider.health_check() is False


def test_setup_logging_does_not_raise() -> None:
    from aibenchmark.app.logging import setup_logging
    setup_logging()


def test_cli_run_main_monkeypatched(monkeypatch, tmp_path: Path) -> None:
    runner = CliRunner()

    class FakeEngine:
        def __init__(self, *args, **kwargs):
            pass

        def list_benchmarks(self):
            return ["coding"]

        def run_benchmark(self, *args, **kwargs):
            from aibenchmark.app.models import BenchmarkResult, ProviderType, Score
            return BenchmarkResult(
                model="demo",
                provider=ProviderType.OLLAMA,
                scores=[Score(benchmark=BenchmarkName.CODING, raw=0.8, normalized=0.8, weight=1.0)],
                details={"raw_score": 0.8, "normalized": 0.8, "evaluation": "", "recommendations": []},
                metadata={"status": "success"},
            )

        def generate_reports(self, results, out_dir):
            (out_dir / "results.json").write_text("[]")
            (out_dir / "results.md").write_text("md")
            (out_dir / "results.csv").write_text("csv")
            return {}

        @property
        def config(self):
            class _C:
                def defaults(self):
                    return {"default_provider": "ollama", "default_model": "demo"}
                def provider_config(self, name):
                    return {"api_key": "fake", "base_url": ""}
            return _C()

    monkeypatch.setenv("OLLAMA_API_KEY", "fake")
    monkeypatch.setattr("aibenchmark.cli.BenchEngine", FakeEngine)
    result = runner.invoke(cli_group, ["run", "main", "-o", str(tmp_path)])
    assert result.exit_code == 0
    assert "Reports written to" in result.output
