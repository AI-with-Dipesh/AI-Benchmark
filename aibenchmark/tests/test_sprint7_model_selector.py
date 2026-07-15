from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.models import BenchmarkName, PluginCategory, ProviderCapabilities, RoutingContext
from aibenchmark.app.model_selector import ModelSelector
from aibenchmark.app.provider_health import HealthTracker, ProviderHealth, ProviderStatus


def _make_selector(provider="ollama", model="llama3"):
    selector = ModelSelector.__new__(ModelSelector)
    selector.config = MagicMock(spec=AppConfig)
    selector.config.routing = {}
    selector.config.model_cost.return_value = (0.0, 0.0)
    selector._registry = MagicMock()
    selector._health = MagicMock()
    selector._health.get.return_value = ProviderHealth(provider_name=provider, status=ProviderStatus.AVAILABLE)
    caps = ProviderCapabilities(context_window=4096, max_output_tokens=1024)
    selector._registry.capabilities.return_value = caps
    selector._registry.list_providers.return_value = [provider]
    selector._registry.list_models.return_value = [model]
    return selector


def test_context_window_excludes_provider_when_prompt_exceeds() -> None:
    selector = _make_selector()
    selector.config.routing = {}
    # prompt_tokens will be estimated from prompt loader
    with patch.object(selector, "_prompt_token_estimate", return_value=5000):
        ctx = RoutingContext(benchmark_name=BenchmarkName.CODING)
        with pytest.raises(ConfigError, match="No eligible provider/model"):
            selector.select(ctx)


def test_context_window_allows_provider_when_fits() -> None:
    selector = _make_selector()
    selector.config.routing = {}
    with patch.object(selector, "_prompt_token_estimate", return_value=100):
        ctx = RoutingContext(benchmark_name=BenchmarkName.CODING)
        plan = selector.select(ctx)
        assert plan.provider == "ollama"


def test_history_score_decorates_candidates() -> None:
    selector = _make_selector()
    selector.config.routing = {}
    with patch.object(selector, "_prompt_token_estimate", return_value=100):
        with patch("aibenchmark.app.history.recent_category_performance", return_value={
            "ollama:llama3": {"normalized": 0.9, "success_rate": 1.0, "estimated_cost": 0.0}
        }):
            ctx = RoutingContext(benchmark_name=BenchmarkName.CODING)
            candidates = selector._candidates(ctx)
            assert candidates[0]["history_score"] > 0.0


def test_tie_break_keys_are_deterministic() -> None:
    candidates = [
        {"provider": "a", "model": "m1", "estimated_cost": 0.1, "capability_score": 0.9, "health": None, "history_score": 0.5},
        {"provider": "b", "model": "m2", "estimated_cost": 0.1, "capability_score": 0.9, "health": None, "history_score": 0.5},
        {"provider": "a", "model": "m2", "estimated_cost": 0.1, "capability_score": 0.9, "health": None, "history_score": 0.5},
    ]
    plan = ModelSelector._cost_aware(candidates, RoutingContext(benchmark_name=BenchmarkName.CODING))
    assert plan.provider == "a"
    assert plan.model == "m1"


def test_fallback_models_populated_for_chosen_provider() -> None:
    candidates = [
        {"provider": "ollama", "model": "llama3", "estimated_cost": 0.0, "capability_score": 1.0, "health": None, "history_score": 0.5},
        {"provider": "ollama", "model": "mistral", "estimated_cost": 0.0, "capability_score": 0.9, "health": None, "history_score": 0.4},
        {"provider": "openrouter", "model": "gpt-4", "estimated_cost": 0.1, "capability_score": 0.8, "health": None, "history_score": 0.3},
    ]
    plan = ModelSelector._cost_aware(candidates, RoutingContext(benchmark_name=BenchmarkName.CODING))
    assert plan.provider == "ollama"
    assert "mistral" in plan.fallback_models
