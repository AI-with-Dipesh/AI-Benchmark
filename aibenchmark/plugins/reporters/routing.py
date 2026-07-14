from __future__ import annotations

from pathlib import Path

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.provider_health import get_health_tracker
from aibenchmark.app.provider_registry import ProviderRegistry


@register(PluginCategory.REPORTER, "routing")
class RoutingReporter:
    plugin_name = "routing"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        from aibenchmark.app.model_selector import ModelSelector
        from aibenchmark.app.models import RoutingContext

        selector = ModelSelector()
        registry = ProviderRegistry()
        health = get_health_tracker()
        lines = ["# Routing Report\n", "## Active Providers\n"]
        for name in registry.list_providers():
            h = health.get(name)
            lines.append(f"- {name}: {h.status.value} | failure={h.failure_rate:.2%}")
        lines.append("\n## Benchmark Routing Plans\n")
        for benchmark in BenchmarkName:
            try:
                plan = selector.select(RoutingContext(benchmark_name=benchmark))
                lines.append(f"### {benchmark.value}\n")
                lines.append(f"- Provider: {plan.provider}")
                lines.append(f"- Model: {plan.model}")
                lines.append(f"- Rationale: {plan.rationale}")
                if plan.fallback_providers:
                    lines.append(f"- Fallbacks: {', '.join(plan.fallback_providers)}")
                lines.append("")
            except Exception as exc:
                lines.append(f"### {benchmark.value}\n")
                lines.append(f"- Error: {exc}\n")
        path.write_text("\n".join(lines) + "\n")
