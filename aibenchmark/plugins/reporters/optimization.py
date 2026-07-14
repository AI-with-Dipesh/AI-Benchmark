from __future__ import annotations

from pathlib import Path
from typing import Any

from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.provider_registry import ProviderRegistry


@register(PluginCategory.REPORTER, "optimization")
class OptimizationReporter:
    plugin_name = "optimization"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        registry = ProviderRegistry()
        lines = ["# Optimization Report\n", "## Cost-Aware Model Ranking\n", ""]

        cost_map: dict[str, list[float]] = {}
        for result in results:
            key = f"{result.provider.value}/{result.model}"
            if result.estimated_cost is not None:
                cost_map.setdefault(key, []).append(result.estimated_cost)

        if cost_map:
            ranked = sorted(cost_map.items(), key=lambda item: sum(item[1]) / len(item[1]))
            lines.append("### Ranked by cost (lowest first)\n")
            for key, costs in ranked:
                avg = sum(costs) / len(costs)
                lines.append(f"- {key}: avg ${avg:.4f} over {len(costs)} run(s)")
            lines.append("")
            cheapest_key, _ = ranked[0]
            lines.append(f"### Recommendation\n")
            lines.append(f"- Cheapest qualified model: **{cheapest_key}**")
            lines.append("")
        else:
            lines.append("### Available models\n")
            lines.append("No cost data available from benchmark runs.\n")
            for name in registry.list_providers():
                try:
                    models = registry.list_models(name)
                except Exception:
                    continue
                lines.append(f"### {name}\n")
                for model in models[:5]:
                    lines.append(f"- {model}")
                if len(models) > 5:
                    lines.append(f"- ... and {len(models) - 5} more")
                lines.append("")

        path.write_text("\n".join(lines) + "\n")
