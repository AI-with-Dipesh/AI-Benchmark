from __future__ import annotations

from pathlib import Path
from typing import Any

from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.provider_registry import ProviderRegistry


@register(PluginCategory.REPORTER, "provider_health")
class ProviderHealthReporter:
    plugin_name = "provider_health"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: Any) -> None:
        registry = ProviderRegistry()
        healths = registry.all_health()
        lines = ["# Provider Health Report", ""]
        for provider, h in sorted(healths.items()):
            lines.append(f"## {provider}")
            lines.append(f"- Status: {h.status}")
            lines.append(f"- Availability: {h.availability:.2%}")
            lines.append(f"- Average Latency: {h.average_latency_ms:.1f}ms" if h.average_latency_ms else "- Average Latency: N/A")
            lines.append(f"- P95: {h.p95_latency_ms:.1f}ms" if h.p95_latency_ms else "- P95: N/A")
            lines.append(f"- P99: {h.p99_latency_ms:.1f}ms" if h.p99_latency_ms else "- P99: N/A")
            lines.append(f"- Failure Rate: {h.failure_rate:.2%}")
            lines.append(f"- Total Checks: {h.total_checks}")
            lines.append(f"- Last Check: {h.last_check}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
