import json
import csv
from pathlib import Path

from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register


@register(PluginCategory.REPORTER, "json")
class JsonReporter:
    plugin_name = "json"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs) -> None:
        data = []
        for r in results:
            data.append(
                {
                    "benchmark": r.model,
                    "model": r.model,
                    "provider": r.provider.value,
                    "overall": r.overall,
                    "scores": [
                        {
                            "benchmark": s.benchmark.value,
                            "raw": s.raw,
                            "normalized": s.normalized,
                            "weight": s.weight,
                            "weighted": s.weighted,
                        }
                        for s in r.scores
                    ],
                    "evaluation": r.details.get("evaluation"),
                    "recommendations": r.details.get("recommendations"),
                    "metadata": r.metadata,
                    "details": r.details,
                }
            )
        path.write_text(json.dumps(data, indent=2))


@register(PluginCategory.REPORTER, "md")
class MarkdownReporter:
    plugin_name = "md"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs) -> None:
        lines = [
            "# Benchmark Results\n",
            "| Model | Provider | Category | Score | Weighted | Evaluation |",
            "|-------|----------|----------|-------|----------|------------|",
        ]
        for r in sorted(results, key=lambda x: x.overall, reverse=True):
            for s in r.scores:
                lines.append(
                    f"| {r.model} | {r.provider.value} | {s.benchmark.value} | {s.normalized:.2f} | {s.weighted:.2f} | {r.details.get('evaluation','')}"
                )
            lines.append(f"| **{r.model}** | **{r.provider.value}** | **overall** | **{r.overall:.2f}** | **{r.overall:.2f}** | |")
        path.write_text("\n".join(lines) + "\n")


@register(PluginCategory.REPORTER, "csv")
class CsvReporter:
    plugin_name = "csv"
    plugin_api_version = "1.0"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs) -> None:
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["model", "provider", "category", "overall", "weighted"])
            for r in sorted(results, key=lambda x: x.overall, reverse=True):
                for s in r.scores:
                    writer.writerow([r.model, r.provider.value, s.benchmark.value, r.overall, s.weighted])
