from __future__ import annotations

import logging
import time
from typing import Any

from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.models import BenchmarkName, PluginCategory, RoutingPlan
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.provider_health import get_health_tracker
from aibenchmark.app.provider_registry import ProviderRegistry
from aibenchmark.interfaces.strategy import BaseStrategy

logger = logging.getLogger(__name__)


@register(PluginCategory.STRATEGY, "execution_policy")
class ExecutionPolicy(BaseStrategy):
    plugin_name = "execution_policy"
    plugin_category = "strategy"
    plugin_priority = 100

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self._registry = ProviderRegistry()
        self._health = get_health_tracker()
        self._cooldowns: dict[str, float] = {}

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        return {"status": "ok"}

    def is_circuit_open(self, provider_name: str) -> bool:
        circuit = self.config.routing.get("circuit_breaker", {})
        if not circuit.get("enabled", True):
            return False
        if provider_name in self._cooldowns:
            cooldown = float(circuit.get("cooldown_seconds", 300))
            if time.time() - self._cooldowns[provider_name] < cooldown:
                return True
        health = self._health.get(provider_name)
        if health.failure_rate > circuit.get("failure_rate_threshold", 0.5):
            return True
        return False

    def record_failure(self, provider_name: str) -> None:
        self._cooldowns[provider_name] = time.time()

    def apply(self, primary_plan: RoutingPlan) -> RoutingPlan:
        circuit = self.config.routing.get("circuit_breaker", {})
        chain = self.config.routing.get("fallback_chain", [])
        if not self.config.routing.get("fallback_enabled", False):
            return primary_plan
        available_fallbacks = []
        for provider_name in chain:
            if not isinstance(provider_name, str):
                continue
            if provider_name == primary_plan.provider:
                continue
            if self._registry.get_plugin(provider_name) is None:
                continue
            if self.is_circuit_open(provider_name):
                continue
            available_fallbacks.append(provider_name)
        return RoutingPlan(
            provider=primary_plan.provider,
            model=primary_plan.model,
            estimated_cost=primary_plan.estimated_cost,
            rationale=primary_plan.rationale,
            fallback_providers=available_fallbacks,
            fallback_models=primary_plan.fallback_models,
        )

    def next_provider(self, plan: RoutingPlan) -> str | None:
        for provider_name in plan.fallback_providers:
            if not self.is_circuit_open(provider_name):
                return provider_name
        return None
