from aibenchmark.interfaces.benchmark import BaseBenchmark
from typing import Any

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, PluginCategory, ResponseObject, Score
from aibenchmark.app.plugin.registry import register


@register(PluginCategory.BENCHMARK, "latency")
class LatencyBenchmark(BaseBenchmark):
    name = BenchmarkName.LATENCY
    plugin_name = "latency"

    plugin_api_version = "1.0"
    def run(self, response: ResponseObject, **kwargs: Any) -> BenchmarkResult:
        latency = response.latency_ms or float("inf")
        normalized = max(0.0, min(1.0, 1.0 - (latency / 5000.0)))
        score = Score(
            benchmark=BenchmarkName.LATENCY,
            raw=latency,
            normalized=normalized,
            weight=1.0,
        )
        return BenchmarkResult(
            model=response.model,
            provider=response.provider,
            scores=[score],
            details={"latency_ms": latency, "normalized": normalized},
        )
