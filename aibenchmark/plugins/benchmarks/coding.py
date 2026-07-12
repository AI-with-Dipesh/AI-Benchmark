from __future__ import annotations

from aibenchmark.interfaces.benchmark import BaseBenchmark
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, PluginCategory, Score
from aibenchmark.app.plugin.registry import register


@register(PluginCategory.BENCHMARK, "coding")
class CodingBenchmark(BaseBenchmark):
    name = BenchmarkName.CODING
    plugin_name = "coding"

    def run(self, response, **kwargs):
        content = response.content or ""
        raw_score = 1.0 if content.strip() else 0.0
        score = Score(
            benchmark=BenchmarkName.CODING,
            raw=raw_score,
            normalized=raw_score,
            weight=1.0,
        )
        return BenchmarkResult(
            model=response.model,
            provider=response.provider,
            scores=[score],
            details={"raw_score": raw_score, "note": "v1 stub"},
        )
