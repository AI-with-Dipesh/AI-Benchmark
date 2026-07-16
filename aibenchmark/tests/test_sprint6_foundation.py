from __future__ import annotations

import threading

import pytest

from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.execution_policy import ExecutionPolicy
from aibenchmark.app.history import HistoryWriter
from aibenchmark.app.model_selector import ModelSelector
from aibenchmark.app.models import BenchmarkName, ProviderCapabilities, RoutingContext, RoutingPlan
from aibenchmark.app.provider_health import HealthTracker, reset_health_tracker


class TestHealthTrackerConcurrency:
    def test_concurrent_record_no_exceptions(self) -> None:
        tracker = HealthTracker(window_size=100)
        errors = []

        def worker(provider: str) -> None:
            try:
                for i in range(200):
                    tracker.record(provider, float(i), i % 3 == 0)
            except Exception as exc:  # pragma: no cover - safety
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(f"p{i}",)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors

    def test_concurrent_get_all_consistent(self) -> None:
        tracker = HealthTracker(window_size=100)
        tracker.record("p1", 50.0, True)
        reads = []

        def reader() -> None:
            for _ in range(100):
                reads.append(tracker.get("p1").average_latency_ms)
                reads.append(len(tracker.all()))

        threads = [threading.Thread(target=reader) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert all(v is not None for v in reads)


class TestHistoryWriter:
    def test_singleton_instance(self) -> None:
        HistoryWriter.reset()
        a = HistoryWriter.instance()
        b = HistoryWriter.instance()
        assert a is b
        HistoryWriter.reset()

    def test_save_and_load(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        HistoryWriter.reset()
        writer = HistoryWriter.instance(tmp_path / "history.db")
        from aibenchmark.app.models import BenchmarkResult, ProviderType, Score

        results = [
            BenchmarkResult(
                model="m1",
                provider=ProviderType.OPENROUTER,
                scores=[Score(benchmark=BenchmarkName.CODING, raw=1.0, normalized=0.8, weight=1.0)],
            )
        ]
        run_id = writer.save_run(results)
        assert run_id > 0
        HistoryWriter.reset()

    def test_concurrent_writes_do_not_corrupt(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        HistoryWriter.reset()
        db = tmp_path / "history.db"
        from aibenchmark.app.models import BenchmarkResult, ProviderType, Score
        errors = []

        def worker(thread_id: int) -> None:
            try:
                writer = HistoryWriter.instance(db)
                for i in range(20):
                    results = [
                        BenchmarkResult(
                            model=f"m{thread_id}",
                            provider=ProviderType.OPENROUTER,
                            scores=[Score(benchmark=BenchmarkName.CODING, raw=float(i), normalized=float(i / 20), weight=1.0)],
                        )
                    ]
                    writer.save_run(results)
            except Exception as exc:  # pragma: no cover - safety
                errors.append(exc)

        threads = [threading.Thread(target=worker, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert not errors
        HistoryWriter.reset()


class TestConfigRouting:
    def test_defaults_when_missing_routing(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({"openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": "https://openrouter.ai/api/v1"}}))
        (cfg_dir / "benchmark.yaml").write_text(yaml.safe_dump({"weights": {"coding": 1}}))
        cfg = AppConfig(cfg_dir)
        assert cfg.routing["strategy"] == "cost_aware"
        assert cfg.routing["parallel"]["enabled"] is False

    def test_invalid_strategy_raises(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({"openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": "https://openrouter.ai/api/v1"}}))
        (cfg_dir / "benchmark.yaml").write_text(yaml.safe_dump({"weights": {"coding": 1}, "routing": {"strategy": "unknown"}}))
        with pytest.raises(ConfigError):
            AppConfig(cfg_dir)

    def test_invalid_cost_ceiling_raises(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({"openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": "https://openrouter.ai/api/v1"}}))
        (cfg_dir / "benchmark.yaml").write_text(yaml.safe_dump({"weights": {"coding": 1}, "routing": {"cost_ceiling": -1}}))
        with pytest.raises(ConfigError):
            AppConfig(cfg_dir)


class TestModelSelector:
    def test_select_returns_routing_plan(self, monkeypatch) -> None:
        monkeypatch.setenv("OPENROUTER_API_KEY", "x")
        from unittest.mock import MagicMock
        fake_registry = MagicMock()
        fake_registry.list_providers.return_value = ["openrouter"]
        fake_registry.capabilities.return_value = ProviderCapabilities(chat=True)
        fake_registry.list_models.return_value = ["gpt-4o"]
        from aibenchmark.app import model_selector as ms
        monkeypatch.setattr(ms, "ProviderRegistry", lambda: fake_registry)
        selector = ModelSelector()
        plan = selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING))
        assert isinstance(plan, RoutingPlan)
        assert plan.provider
        assert plan.model

    def test_capability_first_strategy(self, monkeypatch) -> None:
        from unittest.mock import MagicMock
        fake_registry = MagicMock()
        fake_registry.list_providers.return_value = ["openrouter", "ollama"]
        fake_registry.capabilities.side_effect = lambda name: ProviderCapabilities(chat=True, function_calling=(name == "ollama"))
        fake_registry.list_models.side_effect = lambda name: [f"{name}-model"]
        fake_health = MagicMock()
        fake_health.get.return_value = MagicMock(failure_rate=0.0, status=MagicMock(value="available"))
        from aibenchmark.app import model_selector as ms
        monkeypatch.setattr(ms, "ProviderRegistry", lambda: fake_registry)
        monkeypatch.setattr(ms, "get_health_tracker", lambda: fake_health)
        import yaml
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            from pathlib import Path
            cfg_dir = Path(tmp) / "config"
            cfg_dir.mkdir()
            (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
                "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
                "ollama": {"api_key_env": "OLLAMA_API_KEY", "api_key": "", "base_url": "http://localhost:11434"},
            }))
            (cfg_dir / "benchmark.yaml").write_text(yaml.safe_dump({
                "weights": {"coding": 1},
                "cost": {
                    "openrouter": {"default": {"prompt": 1.0, "completion": 2.0}},
                    "ollama": {"default": {"prompt": 0.0, "completion": 0.0}},
                },
                "routing": {"strategy": "capability_first"},
            }))
            selector = ModelSelector(AppConfig(cfg_dir))
            plan = selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING, required_capabilities=["function_calling"], min_capability_score=0.5))
            assert plan.provider == "ollama"

    def test_health_first_strategy(self, monkeypatch) -> None:
        from unittest.mock import MagicMock
        fake_registry = MagicMock()
        fake_registry.list_providers.return_value = ["openrouter", "ollama"]
        fake_registry.capabilities.return_value = ProviderCapabilities(chat=True)
        fake_registry.list_models.side_effect = lambda name: [f"{name}-model"]
        fake_health = MagicMock()
        fake_health.get.side_effect = lambda name: MagicMock(failure_rate=0.8 if name == "openrouter" else 0.0, status=MagicMock(value="unavailable" if name == "openrouter" else "available"), average_latency_ms=100.0)
        from aibenchmark.app import model_selector as ms
        monkeypatch.setattr(ms, "ProviderRegistry", lambda: fake_registry)
        monkeypatch.setattr(ms, "get_health_tracker", lambda: fake_health)
        import yaml
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as tmp:
            cfg_dir = Path(tmp) / "config"
            cfg_dir.mkdir()
            (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
                "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
                "ollama": {"api_key_env": "OLLAMA_API_KEY", "api_key": "", "base_url": "http://localhost:11434"},
            }))
            (cfg_dir / "benchmark.yaml").write_text(yaml.safe_dump({
                "weights": {"coding": 1},
                "cost": {
                    "openrouter": {"default": {"prompt": 1.0, "completion": 2.0}},
                    "ollama": {"default": {"prompt": 0.0, "completion": 0.0}},
                },
                "routing": {"strategy": "health_first"},
            }))
            selector = ModelSelector(AppConfig(cfg_dir))
            plan = selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING))
            assert plan.provider == "ollama"

    def test_cost_aware_cheapest_first(self, tmp_path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
            "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
            "ollama": {"api_key_env": "OLLAMA_API_KEY", "api_key": "", "base_url": "http://localhost:11434"},
        }))
        benchmark = yaml.safe_dump({
            "weights": {"coding": 1},
            "cost": {
                "openrouter": {"default": {"prompt": 1.0, "completion": 2.0}},
                "ollama": {"default": {"prompt": 0.0, "completion": 0.0}},
            },
            "routing": {"strategy": "cost_aware", "prefer_free": True},
        })
        (cfg_dir / "benchmark.yaml").write_text(benchmark)
        from unittest.mock import MagicMock
        fake_registry = MagicMock()
        fake_registry.list_providers.return_value = ["openrouter", "ollama"]
        fake_registry.capabilities.return_value = ProviderCapabilities(chat=True)
        fake_registry.list_models.side_effect = lambda name: ["m1", "m2"] if name == "openrouter" else ["ollama-model"]
        fake_health = MagicMock()
        fake_health.get.return_value = MagicMock(status=MagicMock(value="available"), failure_rate=0.0)
        from aibenchmark.app import model_selector as ms
        monkeypatch.setattr(ms, "ProviderRegistry", lambda: fake_registry)
        monkeypatch.setattr(ms, "get_health_tracker", lambda: fake_health)
        selector = ModelSelector(AppConfig(cfg_dir))
        plan = selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING, prefer_free=True))
        assert plan.provider == "ollama"

    def test_cost_ceiling_enforced(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
            "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
        }))
        benchmark = yaml.safe_dump({
            "weights": {"coding": 1},
            "cost": {"openrouter": {"default": {"prompt": 1.0, "completion": 2.0}}},
            "routing": {"strategy": "cost_aware", "cost_ceiling": 0.0},
        })
        (cfg_dir / "benchmark.yaml").write_text(benchmark)
        selector = ModelSelector(AppConfig(cfg_dir))
        with pytest.raises(ConfigError):
            selector.select(RoutingContext(benchmark_name=BenchmarkName.CODING, max_cost=0.0))


class TestExecutionPolicy:
    def test_apply_preserves_primary_when_fallback_disabled(self) -> None:
        policy = ExecutionPolicy()
        plan = policy.apply(RoutingPlan(provider="openrouter", model="m1"))
        assert plan.provider == "openrouter"
        assert plan.fallback_providers == []

    def test_circuit_open_blocks_provider(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
            "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
        }))
        benchmark = yaml.safe_dump({
            "weights": {"coding": 1},
            "routing": {"fallback_enabled": True, "fallback_chain": ["openrouter"], "circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5, "cooldown_seconds": 60}},
        })
        (cfg_dir / "benchmark.yaml").write_text(benchmark)
        policy = ExecutionPolicy(AppConfig(cfg_dir))
        policy.record_failure("openrouter")
        assert policy.is_circuit_open("openrouter") is True

    def test_next_provider_skips_circuit_open(self, tmp_path) -> None:  # type: ignore[no-untyped-def]
        import yaml
        cfg_dir = tmp_path / "config"
        cfg_dir.mkdir()
        (cfg_dir / "providers.yaml").write_text(yaml.safe_dump({
            "openrouter": {"api_key_env": "OPENROUTER_API_KEY", "api_key": "x", "base_url": ""},
            "ollama": {"api_key_env": "OLLAMA_API_KEY", "api_key": "", "base_url": "http://localhost:11434"},
        }))
        benchmark = yaml.safe_dump({
            "weights": {"coding": 1},
            "routing": {"fallback_enabled": True, "fallback_chain": ["openrouter", "ollama"], "circuit_breaker": {"enabled": True, "failure_rate_threshold": 0.5, "cooldown_seconds": 60}},
        })
        (cfg_dir / "benchmark.yaml").write_text(benchmark)
        reset_health_tracker()
        policy = ExecutionPolicy(AppConfig(cfg_dir))
        policy.record_failure("openrouter")
        plan = RoutingPlan(provider="openrouter", model="m1", fallback_providers=["openrouter", "ollama"])
        assert policy.next_provider(plan) == "ollama"
