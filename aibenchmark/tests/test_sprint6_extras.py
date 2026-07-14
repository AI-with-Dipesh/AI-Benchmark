from __future__ import annotations

import pytest

from aibenchmark.app.config import ConfigError
from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.execution_policy import ExecutionPolicy
from aibenchmark.app.model_selector import ModelSelector
from aibenchmark.app.models import BenchmarkName, RoutingContext, RoutingPlan
from aibenchmark.app.parallel_executor import ParallelExecutor


class TestBenchEngineStrategyDelegation:
    def test_select_model_delegates_to_strategy(self, monkeypatch) -> None:
        from unittest.mock import MagicMock
        fake_registry = MagicMock()
        fake_registry.list_providers.return_value = ["openrouter"]
        fake_registry.capabilities.return_value = type("C", (), {"chat": True, "flags": lambda self: ["chat"]})()
        fake_registry.list_models.return_value = ["m1"]
        fake_health = MagicMock()
        fake_health.get.return_value = MagicMock(failure_rate=0.0, status=MagicMock(value="available"))
        from aibenchmark.app import model_selector as ms
        monkeypatch.setattr(ms, "ProviderRegistry", lambda: fake_registry)
        monkeypatch.setattr(ms, "get_health_tracker", lambda: fake_health)
        engine = BenchEngine()
        plan = engine.select_model({"benchmark_name": BenchmarkName.CODING.value})
        assert "provider" in plan
        assert "model" in plan

    def test_apply_policy_delegates_to_strategy(self) -> None:
        engine = BenchEngine()
        plan = engine.apply_policy({"provider": "openrouter", "model": "m1"})
        assert "provider" in plan
        assert "model" in plan


class TestParallelExecutor:
    def test_map_applies_function_to_all(self) -> None:
        executor = ParallelExecutor(max_workers=2)
        results = executor.map(lambda x: x * 2, [1, 2, 3, 4])
        assert results == [2, 4, 6, 8]

    def test_map_isolates_failures(self) -> None:
        executor = ParallelExecutor(max_workers=2)

        def task(x: int) -> int:
            if x == 3:
                raise RuntimeError("boom")
            return x * 2

        results = executor.map(task, [1, 2, 3, 4])
        assert results[0] == 2
        assert results[1] == 4
        assert results[2] is None
        assert results[3] == 8

    def test_map_deterministic_order(self) -> None:
        executor = ParallelExecutor(max_workers=2)
        results = executor.map(lambda x: x, [10, 20, 30])
        assert results == [10, 20, 30]


class TestReportersRegistered:
    def test_litellm_config_reporter_registered(self) -> None:
        import aibenchmark.plugins  # noqa: F401
        from aibenchmark.app.plugin.registry import get_manager
        from aibenchmark.app.models import PluginCategory

        mgr = get_manager()
        assert mgr.get(PluginCategory.REPORTER, "litellm_config") is not None

    def test_routing_reporter_registered(self) -> None:
        import aibenchmark.plugins  # noqa: F401
        from aibenchmark.app.plugin.registry import get_manager
        from aibenchmark.app.models import PluginCategory

        mgr = get_manager()
        assert mgr.get(PluginCategory.REPORTER, "routing") is not None

    def test_optimization_reporter_registered(self) -> None:
        import aibenchmark.plugins  # noqa: F401
        from aibenchmark.app.plugin.registry import get_manager
        from aibenchmark.app.models import PluginCategory

        mgr = get_manager()
        assert mgr.get(PluginCategory.REPORTER, "optimization") is not None

    def test_litellm_config_generates_yaml(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import aibenchmark.plugins  # noqa: F401
        from aibenchmark.app.engine import BenchEngine
        from aibenchmark.app.models import BenchmarkResult, PluginCategory
        from aibenchmark.app.plugin.registry import get_manager

        mgr = get_manager()
        cls = mgr.get(PluginCategory.REPORTER, "litellm_config")
        assert cls is not None
        reporter = cls()
        out = tmp_path / "litellm.yaml"
        reporter.generate([], out)
        assert out.exists()
        assert "model_list" in out.read_text()


class TestFallbackIntegration:
    def test_fallback_after_retry_exhaustion(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
            "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
            "ollama": {"api_key_env": "OLLAMA_API_KEY", "api_key": "", "base_url": "http://localhost:11434"},
        }))
        (cfg_dir / "benchmark.yaml").write_text(yaml.safe_dump({
            "weights": {"coding": 1},
            "retry": {"retry_count": 1},
            "routing": {
                "fallback_enabled": True,
                "fallback_chain": ["ollama"],
                "circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5, "cooldown_seconds": 60},
            },
        }))

        import os
        os.environ.setdefault("OPENROUTER_API_KEY", "x")
        os.environ.setdefault("OLLAMA_API_KEY", "")

        calls = []

        class FakeProvider:
            def __init__(self, name: str, fail: bool) -> None:
                self._name = name
                self._fail = fail

            def chat(self, model, messages, **kwargs):
                calls.append(self._name)
                if self._fail:
                    raise ConnectionError("connection")
                from aibenchmark.app.models import ResponseObject, ProviderType
                return ResponseObject(provider=ProviderType(self._name.upper()), model=model, content="ok", latency_ms=10.0)

            def list_models(self):
                return ["m1"]

            def capabilities(self):
                from aibenchmark.app.models import ProviderCapabilities
                return ProviderCapabilities(chat=True)

            def validate_configuration(self):
                return {"valid": True}

            def metadata(self):
                return {"provider_name": self._name}

        from unittest.mock import MagicMock
        fake_registry = MagicMock()
        fake_registry.list_providers.return_value = ["openrouter", "ollama"]
        fake_registry.list_models.return_value = ["m1"]
        fake_registry.capabilities.return_value = type("C", (), {"chat": True, "flags": lambda self: ["chat"]})()
        fake_registry.get_plugin.side_effect = lambda name: FakeProvider(name, fail=(name == "openrouter"))
        fake_health = MagicMock()
        fake_health.get.return_value = MagicMock(failure_rate=0.0, status=MagicMock(value="available"))

        class FakeExecutionPolicy:
            def __init__(self, *args, **kwargs):
                pass

            def apply(self, plan):
                return plan

            @staticmethod
            def is_circuit_open(provider_name: str) -> bool:
                return False

        from aibenchmark.app import model_selector as ms
        monkeypatch.setattr(ms, "ProviderRegistry", lambda: fake_registry)
        monkeypatch.setattr(ms, "get_health_tracker", lambda: fake_health)

        def fake_init_provider(provider_name: str, **kwargs):
            return FakeProvider(provider_name, fail=(provider_name == "openrouter"))

        engine = BenchEngine(cfg_dir)
        monkeypatch.setattr(engine, "_init_provider", fake_init_provider)
        monkeypatch.setattr(engine, "_health_tracker", fake_health)
        monkeypatch.setattr(engine, "_get_strategy", lambda category, name: FakeExecutionPolicy if name == "execution_policy" else None)
        result = engine.run_benchmark("openrouter", "m1", "coding", [{"role": "user", "content": "hi"}])
        assert "ollama" in calls or result.provider.value == "ollama"


class TestParallelConfigGate:
    def test_run_parallel_raises_when_disabled(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
            "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
        }))
        (cfg_dir / "benchmark.yaml").write_text(yaml.safe_dump({
            "weights": {"coding": 1},
            "routing": {"parallel": {"enabled": False, "max_workers": 2}},
        }))
        engine = BenchEngine(cfg_dir)
        with pytest.raises(ConfigError, match="disabled in configuration"):
            engine.run_parallel(["openrouter"], "m1", ["coding"], [{"role": "user", "content": "hello"}])
