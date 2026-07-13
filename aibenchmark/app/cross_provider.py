from __future__ import annotations

import logging
from typing import Any

from aibenchmark.app.models import BenchmarkResult, ProviderType, ProviderHealth
from aibenchmark.app.provider_registry import ProviderRegistry

logger = logging.getLogger(__name__)


class CrossProviderBenchmark:
    def __init__(self) -> None:
        self.registry = ProviderRegistry()

    def compare_providers(
        self,
        providers: list[str],
        models: dict[str, list[str]],
    ) -> dict[str, Any]:
        comparison: dict[str, Any] = {
            "providers": providers,
            "models": models,
            "capabilities": {},
            "health": {},
            "metadata": {},
            "overall_ranking": [],
        }
        for p in providers:
            comparison["capabilities"][p] = self.registry.capabilities(p)
            comparison["health"][p] = self.registry.health(p)
            comparison["metadata"][p] = self.registry.metadata(p)
        comparison["overall_ranking"] = self._rank_providers(providers, comparison["health"])
        return comparison

    def compare_with_results(
        self,
        providers: list[str],
        models: dict[str, list[str]],
        results: list[BenchmarkResult],
    ) -> dict[str, Any]:
        comparison = self.compare_providers(providers, models)
        comparison["category_comparison"] = self._category_comparison(providers, results)
        return comparison

    def _category_comparison(self, providers: list[str], results: list[BenchmarkResult]) -> dict[str, Any]:
        from collections import defaultdict

        buckets: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
        for result in results:
            provider_key = result.provider.value if isinstance(result.provider, ProviderType) else str(result.provider)
            if provider_key not in providers:
                continue
            for score in result.scores:
                category = score.benchmark.value
                buckets[provider_key][category].append(score.normalized)
        summary: dict[str, Any] = {}
        for provider in providers:
            summary[provider] = {}
            for category, values in buckets.get(provider, {}).items():
                if values:
                    summary[provider][category] = {
                        "count": len(values),
                        "average": sum(values) / len(values),
                        "min": min(values),
                        "max": max(values),
                    }
        return summary

    def _rank_providers(self, providers: list[str], health_map: dict[str, ProviderHealth]) -> list[dict[str, Any]]:
        ranking: list[dict[str, Any]] = []
        for p in providers:
            health = health_map.get(p) or self.registry.health(p)
            caps = self.registry.capabilities(p)
            score = (
                health.availability * 0.4
                + (health.average_latency_ms or 9999.0) / 10000.0 * 0.3
                + (1.0 - health.failure_rate) * 0.3
            )
            ranking.append(
                {
                    "provider": p,
                    "score": score,
                    "availability": health.availability,
                    "latency_ms": health.average_latency_ms,
                    "failure_rate": health.failure_rate,
                    "capabilities": caps.flags(),
                }
            )
        ranking.sort(key=lambda r: r["score"], reverse=True)
        for i, entry in enumerate(ranking, start=1):
            entry["rank"] = i
        return ranking
