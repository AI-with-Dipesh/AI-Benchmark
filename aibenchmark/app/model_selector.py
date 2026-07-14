from __future__ import annotations

import logging
from typing import Any

from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.models import BenchmarkName, PluginCategory, ProviderCapabilities, RoutingContext, RoutingPlan
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.provider_health import get_health_tracker
from aibenchmark.app.provider_registry import ProviderRegistry
from aibenchmark.interfaces.strategy import BaseStrategy

logger = logging.getLogger(__name__)


@register(PluginCategory.STRATEGY, "model_selector")
class ModelSelector(BaseStrategy):
    plugin_name = "model_selector"
    plugin_category = "strategy"
    plugin_priority = 100

    def __init__(self, config: AppConfig | None = None) -> None:
        self.config = config or AppConfig()
        self._registry = ProviderRegistry()
        self._health = get_health_tracker()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        ctx = context if isinstance(context, RoutingContext) else RoutingContext(**context)
        return self.select(ctx).__dict__

    def select(self, context: RoutingContext) -> RoutingPlan:
        strategy = self.config.routing.get("strategy", "cost_aware")
        candidates = self._candidates(context)
        if not candidates:
            raise ConfigError(f"No eligible provider/model found for {context.benchmark_name.value}")
        if strategy == "cost_aware":
            plan = self._cost_aware(candidates, context)
        elif strategy == "capability_first":
            plan = self._capability_first(candidates, context)
        elif strategy == "health_first":
            plan = self._health_first(candidates, context)
        elif strategy == "round_robin":
            plan = self._round_robin(candidates, context)
        else:
            plan = self._cost_aware(candidates, context)
        if context.max_cost and (plan.estimated_cost or 0.0) > context.max_cost:
            raise ConfigError(
                f"Selected plan exceeds cost ceiling: {plan.estimated_cost:.4f} > {context.max_cost:.4f}"
            )
        return plan

    def _candidates(self, context: RoutingContext) -> list[dict[str, Any]]:
        candidates: list[dict[str, Any]] = []
        names = [context.provider_name] if context.provider_name else self._registry.list_providers()
        for provider_name in names:
            try:
                caps = self._registry.capabilities(provider_name)
            except ValueError:
                continue
            models = self._registry.list_models(provider_name)
            if not models:
                continue
            score = self._capability_score(caps, context)
            if score < context.min_capability_score:
                continue
            health = self._health.get(provider_name)
            if health.status.value == "unavailable":
                continue
            if context.prefer_free:
                paid = [m for m in models if self._is_paid(provider_name, m)]
                models = [m for m in models if m not in paid] or models
            for model in models:
                est = 0.0
                try:
                    pp, cp = self.config.model_cost(provider_name, model)
                    est = (8192 / 1000.0) * pp + (1024 / 1000.0) * cp
                except Exception:
                    pass
                candidates.append(
                    {
                        "provider": provider_name,
                        "model": model,
                        "capability_score": score,
                        "estimated_cost": est,
                        "health": health,
                        "capabilities": caps,
                    }
                )
        return candidates

    @staticmethod
    def _capability_score(caps: ProviderCapabilities, context: RoutingContext) -> float:
        if not context.required_capabilities:
            return 1.0
        flags = set(caps.flags())
        required = set(context.required_capabilities)
        if not required:
            return 1.0
        return len(flags & required) / len(required)

    def _is_paid(self, provider: str, model: str) -> bool:
        try:
            pp, cp = self.config.model_cost(provider, model)
            return (pp + cp) > 0
        except Exception:
            return False

    @staticmethod
    def _cost_aware(candidates: list[dict[str, Any]], context: RoutingContext) -> RoutingPlan:
        candidates.sort(key=lambda x: (x["estimated_cost"], -x["capability_score"]))
        chosen = candidates[0]
        fallbacks = [c["provider"] for c in candidates[1:4] if c["provider"] != chosen["provider"]]
        return RoutingPlan(
            provider=chosen["provider"],
            model=chosen["model"],
            estimated_cost=chosen["estimated_cost"],
            rationale=f"cost_aware: selected cheapest qualified model after capability filtering (cost={chosen['estimated_cost']:.4f})",
            fallback_providers=fallbacks,
            fallback_models=[],
        )

    @staticmethod
    def _capability_first(candidates: list[dict[str, Any]], context: RoutingContext) -> RoutingPlan:
        candidates.sort(key=lambda x: (-x["capability_score"], x["estimated_cost"]))
        chosen = candidates[0]
        fallbacks = [c["provider"] for c in candidates[1:4] if c["provider"] != chosen["provider"]]
        return RoutingPlan(
            provider=chosen["provider"],
            model=chosen["model"],
            estimated_cost=chosen["estimated_cost"],
            rationale=f"capability_first: selected highest capability score ({chosen['capability_score']:.2f})",
            fallback_providers=fallbacks,
            fallback_models=[],
        )

    def _health_first(self, candidates: list[dict[str, Any]], context: RoutingContext) -> RoutingPlan:
        def sort_key(x: dict[str, Any]) -> tuple[float, float, float]:
            health = x["health"]
            failure = health.failure_rate if health else 0.0
            latency = health.average_latency_ms or 0.0
            cost = x["estimated_cost"]
            return (failure, latency, cost)

        candidates.sort(key=sort_key)
        chosen = candidates[0]
        fallbacks = [c["provider"] for c in candidates[1:4] if c["provider"] != chosen["provider"]]
        return RoutingPlan(
            provider=chosen["provider"],
            model=chosen["model"],
            estimated_cost=chosen["estimated_cost"],
            rationale=f"health_first: selected lowest failure rate provider ({chosen['health'].failure_rate:.2%})",
            fallback_providers=fallbacks,
            fallback_models=[],
        )

    @staticmethod
    def _round_robin(candidates: list[dict[str, Any]], context: RoutingContext) -> RoutingPlan:
        index = hash((context.benchmark_name.value, context.provider_name)) % len(candidates)
        chosen = candidates[index]
        fallbacks = [c["provider"] for c in candidates[(index + 1) : (index + 4)] if c["provider"] != chosen["provider"]]
        return RoutingPlan(
            provider=chosen["provider"],
            model=chosen["model"],
            estimated_cost=chosen["estimated_cost"],
            rationale="round_robin: deterministic selection by benchmark hash",
            fallback_providers=fallbacks,
            fallback_models=[],
        )
