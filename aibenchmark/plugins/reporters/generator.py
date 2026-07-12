import json
from pathlib import Path

from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register


@register(PluginCategory.REPORTER, "json")
class JsonReporter:
    plugin_name = "json"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs):
        data = [
            {"model": r.model, "provider": r.provider.value, "overall": r.overall, "details": r.details}
            for r in results
        ]
        path.write_text(json.dumps(data, indent=2))


@register(PluginCategory.REPORTER, "md")
class MarkdownReporter:
    plugin_name = "md"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs):
        lines = ["# Benchmark Results\n", "| Model | Provider | Overall |", "|-------|----------|---------|"]
        for r in sorted(results, key=lambda x: x.overall, reverse=True):
            lines.append(f"| {r.model} | {r.provider.value} | {r.overall:.2f} |")
        path.write_text("\n".join(lines) + "\n")


@register(PluginCategory.REPORTER, "csv")
class CsvReporter:
    plugin_name = "csv"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs):
        lines = ["model,provider,overall"]
        for r in sorted(results, key=lambda x: x.overall, reverse=True):
            lines.append(f"{r.model},{r.provider.value},{r.overall:.2f}")
        path.write_text("\n".join(lines) + "\n")
