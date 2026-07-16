from aibenchmark.interfaces.benchmark import BaseBenchmark
from aibenchmark.app.evaluation import GeneralEvaluator
from typing import Any

from aibenchmark.app.models import BenchmarkName, BenchmarkResult, PluginCategory, ResponseObject, Score
from aibenchmark.app.plugin.registry import register


@register(PluginCategory.BENCHMARK, "general")
class GeneralBenchmark(BaseBenchmark):
    name = BenchmarkName.GENERAL
    plugin_name = "general"

    plugin_api_version = "1.0"
    def run(self, response: ResponseObject, **kwargs: Any) -> BenchmarkResult:
        prompt = kwargs.get("prompt", {})
        evaluator = GeneralEvaluator(self.name.value, prompt, response.content or "")
        result = evaluator.evaluate()
        score = Score(
            benchmark=BenchmarkName.GENERAL,
            raw=result.score,
            normalized=result.normalized,
            weight=1.0,
        )
        return BenchmarkResult(
            model=response.model,
            provider=response.provider,
            scores=[score],
            details={"raw_score": result.raw.get("score", result.score), **result.metadata},
        )
