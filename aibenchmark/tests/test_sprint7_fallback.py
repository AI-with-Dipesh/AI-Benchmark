from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.execution_policy import ExecutionPolicy
from aibenchmark.app.models import PluginCategory, RoutingPlan


def test_execution_policy_model_first_populates_fallback_models() -> None:
    policy = ExecutionPolicy.__new__(ExecutionPolicy)
    policy.config = MagicMock()
    policy.config.routing = {
        "strategy": "model_first",
        "fallback": {"strategy": "model_first"},
        "fallback_enabled": True,
        "fallback_chain": ["openrouter"],
    }
    policy._registry = MagicMock()
    policy._registry.get_plugin.return_value = MagicMock()
    policy._cooldowns = {}
    policy._health = MagicMock()
    policy._health.get.return_value = MagicMock(failure_rate=0.1)
    policy._registry.list_models.return_value = ["gpt-4", "gpt-3.5"]
    plan = RoutingPlan(provider="ollama", model="llama3", fallback_providers=["openrouter"], fallback_models=[])
    result = policy.apply(plan)
    assert "llama3" not in result.fallback_models
    assert "gpt-4" in result.fallback_models


def test_execution_policy_provider_first_preserves_empty_models() -> None:
    policy = ExecutionPolicy.__new__(ExecutionPolicy)
    policy.config = MagicMock()
    policy.config.routing = {"strategy": "provider_first", "fallback_enabled": True, "fallback_chain": ["openrouter"]}
    policy._registry = MagicMock()
    policy._registry.get_plugin.return_value = MagicMock()
    policy._cooldowns = {}
    policy._health = MagicMock()
    policy._health.get.return_value = MagicMock(failure_rate=0.1)
    plan = RoutingPlan(provider="ollama", model="llama3", fallback_providers=["openrouter"], fallback_models=[])
    result = policy.apply(plan)
    assert result.fallback_models == []


def test_engine_fallback_attempts_provider_first() -> None:
    engine = BenchEngine.__new__(BenchEngine)
    engine.config = MagicMock()
    engine.config.routing = {"fallback": {"strategy": "provider_first"}}
    plan = RoutingPlan(provider="ollama", model="llama3", fallback_providers=["openrouter", "nvidia"], fallback_models=["gpt-4"])
    attempts = engine._fallback_attempts(plan, "ollama", "llama3")
    assert attempts[0] == ("openrouter", "llama3")
    assert attempts[1] == ("nvidia", "llama3")
    assert attempts[2] == ("openrouter", "gpt-4")


def test_engine_fallback_attempts_model_first() -> None:
    engine = BenchEngine.__new__(BenchEngine)
    engine.config = MagicMock()
    engine.config.routing = {"fallback": {"strategy": "model_first"}}
    plan = RoutingPlan(provider="ollama", model="llama3", fallback_providers=["openrouter", "nvidia"], fallback_models=["gpt-4"])
    attempts = engine._fallback_attempts(plan, "ollama", "llama3")
    assert attempts[0] == ("ollama", "gpt-4")
    assert attempts[1] == ("openrouter", "llama3")


def test_engine_fallback_attempts_hybrid() -> None:
    engine = BenchEngine.__new__(BenchEngine)
    engine.config = MagicMock()
    engine.config.routing = {"fallback": {"strategy": "hybrid"}}
    plan = RoutingPlan(provider="ollama", model="llama3", fallback_providers=["openrouter"], fallback_models=["gpt-4"])
    attempts = engine._fallback_attempts(plan, "ollama", "llama3")
    assert ("openrouter", "llama3") in attempts
    assert ("ollama", "gpt-4") in attempts
    assert ("openrouter", "gpt-4") in attempts
