from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.cross_provider import CrossProviderBenchmark


@register(PluginCategory.REPORTER, "provider_comparison")
class ProviderComparisonReporter:
    plugin_name = "provider_comparison"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: Any) -> None:
        providers = kwargs.get("providers", ["nvidia", "openrouter", "ollama", "huggingface"])
        models = kwargs.get("models", {})
        bench = CrossProviderBenchmark()
        if results:
            comparison = bench.compare_with_results(providers, models, results)
        else:
            comparison = bench.compare_providers(providers, models)
        lines = [self._header(comparison)]
        lines.append(self._rankings_section(comparison["overall_ranking"]))
        lines.append(self._capabilities_section(comparison["capabilities"]))
        lines.append(self._health_section(comparison["health"]))
        lines.append(self._cost_section(comparison["metadata"], results))
        lines.append(self._token_efficiency_section(results))
        if comparison.get("category_comparison"):
            lines.append(self._category_section(comparison["category_comparison"]))
        lines.append(self._metadata_section(comparison["metadata"]))
        lines.append(self._footer())
        path.write_text("\n".join(lines), encoding="utf-8")

    def _header(self, comparison: dict[str, Any]) -> str:
        lines = [
            "# Provider Comparison Report",
            "",
            f"Providers: {', '.join(comparison['providers'])}",
            f"Models: {json.dumps(comparison['models'], indent=2)}",
            "",
        ]
        return "\n".join(lines)

    def _rankings_section(self, rankings: list[dict[str, Any]]) -> str:
        lines = ["## Overall Ranking", ""]
        for entry in rankings:
            lines.append(
                f"#{entry['rank']} {entry['provider']}: score={entry['score']:.4f} | "
                f"availability={entry['availability']:.2%} | latency={entry['latency_ms'] or 'N/A'}ms"
            )
        lines.append("")
        return "\n".join(lines)

    def _capabilities_section(self, capabilities: dict[str, Any]) -> str:
        lines = ["## Capabilities", ""]
        for provider, caps in capabilities.items():
            flags = caps.flags() if hasattr(caps, "flags") else []
            ctx = caps.context_window if hasattr(caps, "context_window") else None
            lines.append(f"- {provider}: {', '.join(flags) if flags else 'standard'} (context: {ctx or 'unknown'})")
        lines.append("")
        return "\n".join(lines)

    def _health_section(self, healths: dict[str, Any]) -> str:
        lines = ["## Health Status", ""]
        for provider, h in healths.items():
            lines.append(f"- {provider}: {h.status} | failure_rate={h.failure_rate:.2%} | total_checks={h.total_checks}")
        lines.append("")
        return "\n".join(lines)

    def _category_section(self, category_comparison: dict[str, Any]) -> str:
        lines = ["## Category Comparison", ""]
        for provider, categories in category_comparison.items():
            if not categories:
                continue
            lines.append(f"### {provider}")
            for category, stats in categories.items():
                lines.append(f"- {category}: avg={stats['average']:.3f} min={stats['min']:.3f} max={stats['max']:.3f}")
            lines.append("")
        return "\n".join(lines)

    def _metadata_section(self, metadata: dict[str, Any]) -> str:
        lines = ["## Metadata", ""]
        for provider, meta in metadata.items():
            ep = meta.get("endpoint", "N/A")
            ctx = meta.get("context_window", "N/A")
            lines.append(f"- {provider}: endpoint={ep}, context_window={ctx}")
        lines.append("")
        return "\n".join(lines)

    def _cost_section(self, metadata: dict[str, Any], results: list[BenchmarkResult]) -> str:
        lines = ["## Cost Comparison", ""]
        by_provider: dict[str, float] = {}
        for result in results:
            key = result.provider.value if hasattr(result.provider, "value") else str(result.provider)
            by_provider[key] = by_provider.get(key, 0.0) + (result.estimated_cost or 0.0)
        for provider, meta in metadata.items():
            pricing = meta.get("pricing", {})
            prompt_price = pricing.get("prompt_price_per_1k")
            completion_price = pricing.get("completion_price_per_1k")
            cost = by_provider.get(provider, 0.0)
            parts = [f"- {provider}: estimated_cost={cost:.4f}"]
            if prompt_price is not None:
                parts.append(f"prompt=${prompt_price}/1k")
            if completion_price is not None:
                parts.append(f"completion=${completion_price}/1k")
            lines.append(" ".join(parts))
        lines.append("")
        return "\n".join(lines)

    def _token_efficiency_section(self, results: list[BenchmarkResult]) -> str:
        lines = ["## Token Efficiency", ""]
        by_provider: dict[str, dict[str, float | int]] = {}
        for result in results:
            key = result.provider.value if hasattr(result.provider, "value") else str(result.provider)
            bucket = by_provider.setdefault(key, {"prompt": 0, "completion": 0, "latency": 0.0, "count": 0})
            bucket["prompt"] += result.prompt_tokens or 0
            bucket["completion"] += result.completion_tokens or 0
            latency = result.metadata.get("latency_ms") or 0.0
            bucket["latency"] += latency
            bucket["count"] += 1
        for provider, bucket in by_provider.items():
            total = int(bucket["prompt"]) + int(bucket["completion"])
            latency = float(bucket["latency"])
            tps = total / latency if latency > 0 else 0.0
            lines.append(f"- {provider}: total_tokens={total}, tokens_per_second={tps:.2f}")
        lines.append("")
        return "\n".join(lines)

    def _footer(self) -> str:
        lines = ["---", "*Generated by AI Benchmark Suite - Sprint 5*"]
        return "\n".join(lines)
