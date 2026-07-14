from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.models import (
    BenchmarkName,
    BenchmarkResult,
    PluginCategory,
    ProviderType,
    ResponseObject,
    Score,
)
from aibenchmark.app.plugin.registry import get_manager

logger = logging.getLogger(__name__)


class BenchEngine:
    def __init__(self, config_dir: Path | None = None) -> None:
        import aibenchmark.plugins  # noqa: F401 - trigger built-in plugin registration
        from aibenchmark.app.execution_policy import ExecutionPolicy  # noqa: F401
        from aibenchmark.app.model_selector import ModelSelector  # noqa: F401
        from aibenchmark.app.provider_health import get_health_tracker

        self.plugins = get_manager()
        self._health_tracker = get_health_tracker()
        try:
            self.config = AppConfig(config_dir)
        except ConfigError as exc:
            raise RuntimeError(f"Benchmark configuration failed: {exc}") from exc
        self.retry_policy = self.config.retry
        self.timeout_policy = self.config.timeouts

    def _get_strategy(self, category: PluginCategory, name: str) -> type | None:
        return self.plugins.get(category, name)

    def select_model(self, context: dict[str, Any]) -> dict[str, Any]:
        from aibenchmark.app.model_selector import ModelSelector
        from aibenchmark.app.models import BenchmarkName, RoutingContext

        strategy = self._get_strategy(PluginCategory.STRATEGY, "model_selector")
        selector: ModelSelector = strategy(self.config) if strategy else ModelSelector(self.config)
        if isinstance(context, dict) and isinstance(context.get("benchmark_name"), str):
            ctx = RoutingContext(benchmark_name=BenchmarkName(context["benchmark_name"]), **{k: v for k, v in context.items() if k != "benchmark_name"})
        else:
            ctx = context if isinstance(context, RoutingContext) else RoutingContext(**context)
        return selector.select(ctx).__dict__

    def apply_policy(self, plan: dict[str, Any]) -> dict[str, Any]:
        from aibenchmark.app.execution_policy import ExecutionPolicy
        from aibenchmark.app.models import RoutingPlan

        strategy = self._get_strategy(PluginCategory.STRATEGY, "execution_policy")
        policy: ExecutionPolicy = strategy() if strategy else ExecutionPolicy(self.config)
        p = plan if isinstance(plan, RoutingPlan) else RoutingPlan(**plan)
        result = policy.apply(p)
        return result.__dict__

    def _record_retry_health(self, provider_name: str, retry_count: int, result: BenchmarkResult, success: bool) -> None:
        if retry_count > 0:
            latency = result.metadata.get("latency_ms") or 0.0
            self._health_tracker.record(provider_name, latency, success, is_retry=True)

    def list_providers(self) -> list[str]:
        return self.plugins.list_names(PluginCategory.PROVIDER)

    def list_benchmarks(self) -> list[str]:
        return self.plugins.list_names(PluginCategory.BENCHMARK)

    def list_reporters(self) -> list[str]:
        return self.plugins.list_names(PluginCategory.REPORTER)

    def _init_provider(self, provider_name: str, **kwargs: Any) -> Any:
        cls = self.plugins.get(PluginCategory.PROVIDER, provider_name)
        if cls is None:
            raise ValueError(f"Unknown provider: {provider_name}")

        cfg = self.config.provider_config(provider_name)
        api_key = cfg.get("api_key", "")
        base_url = cfg.get("base_url", "")
        if not api_key:
            api_key_env = cfg.get("api_key_env", "API_KEY")
            logger.warning("API key for provider '%s' is missing; set %s", provider_name, api_key_env)
            raise ValueError(f"Missing API key for provider '{provider_name}'. Set {api_key_env}.")
        try:
            return cls(api_key=api_key, base_url=base_url, **kwargs)
        except Exception as exc:
            raise RuntimeError(f"Failed to initialize provider '{provider_name}': {exc}") from exc

    def _load_prompt(self, benchmark_name: BenchmarkName | str) -> dict[str, Any]:
        from aibenchmark.app.prompts import PromptLoader
        loader = PromptLoader()
        prompt = loader.load(benchmark_name)
        if prompt is None:
            return {}
        return {"system": prompt.system, "user": prompt.user, "expected": getattr(prompt, "expected", None), "metadata": getattr(prompt, "metadata", None)}

    def _apply_run_defaults(self, kwargs: dict[str, Any]) -> dict[str, Any]:
        defaults = self.config.run_defaults
        if "temperature" not in kwargs and defaults.get("temperature") is not None:
            kwargs["temperature"] = defaults["temperature"]
        if "top_p" not in kwargs and defaults.get("top_p") is not None:
            kwargs["top_p"] = defaults["top_p"]
        if "seed" not in kwargs and defaults.get("seed") is not None:
            kwargs["seed"] = defaults["seed"]
        return kwargs

    def _populate_metadata(self, result: BenchmarkResult, response: ResponseObject | None, benchmark_start: float, benchmark_name: BenchmarkName | None = None) -> None:
        latency_ms = None
        if response and response.latency_ms is not None:
            latency_ms = response.latency_ms
        elif benchmark_start:
            latency_ms = (time.perf_counter() - benchmark_start) * 1000

        result.metadata.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        if latency_ms is not None:
            result.metadata.setdefault("latency_ms", latency_ms)

        # reproducibility
        result.model_version = None  # provider does not expose version in current interface
        result.prompt_version = self.config.prompt_version(benchmark_name) if benchmark_name else None
        result.benchmark_version = self.config.benchmark_version

        # run params
        rd = self.config.run_defaults
        result.temperature = rd.get("temperature")
        result.top_p = rd.get("top_p")
        seed = rd.get("seed")
        result.seed = int(seed) if seed is not None else None

        # token accounting
        if response:
            result.prompt_tokens = response.tokens_in
            result.completion_tokens = response.tokens_out
        result.total_tokens = (result.prompt_tokens or 0) + (result.completion_tokens or 0)

        # cost
        try:
            pp, cp = self.config.model_cost(result.provider.value, result.model)
            result.estimated_cost = CostEstimator.estimate(
                prompt_tokens=result.prompt_tokens or 0,
                completion_tokens=result.completion_tokens or 0,
                prompt_price_per_1k=pp,
                completion_price_per_1k=cp,
            )
        except Exception as exc:
            logger.debug("Cost estimation failed: %s", exc)

        # evaluation, objective validation, confidence
        if result.scores:
            score_obj = result.scores[0]
            result.objective_validation = (result.details.get("objective") if isinstance(result.details, dict) else None)
            result.evaluation = score_obj.benchmark.value
            normalized = score_obj.normalized
            result.confidence = min(1.0, 0.5 + float(normalized) * 0.5)

    def run_benchmark(
        self,
        provider_name: str,
        model: str,
        benchmark_name: BenchmarkName | str,
        messages: list[dict[str, Any]],
        *,
        _fallback_depth: int = 0,
        **kwargs: Any,
    ) -> BenchmarkResult:
        provider = self._init_provider(provider_name)
        benchmark_name_enum = benchmark_name if isinstance(benchmark_name, BenchmarkName) else BenchmarkName(benchmark_name)
        benchmark_cls = self.plugins.get(PluginCategory.BENCHMARK, benchmark_name_enum.value)
        if benchmark_cls is None:
            raise ValueError(f"Unknown benchmark: {benchmark_name_enum}")

        prompt = self._load_prompt(benchmark_name_enum)
        prompt_meta = {
            "system": prompt.get("system", ""),
            "user": prompt.get("user", ""),
            "expected": prompt.get("expected"),
            "metadata": prompt.get("metadata"),
        }
        if prompt.get("system"):
            messages = [{"role": "system", "content": prompt["system"]}] + messages
        if prompt.get("user"):
            fallback = messages[-1]["content"] if messages else ""
            messages[-1] = {"role": "user", "content": prompt["user"] or fallback}

        self._apply_run_defaults(kwargs)
        kwargs.pop("benchmark", None)
        kwargs.pop("out", None)

        attempt = 0
        last_exc: Exception | None = None
        response: ResponseObject | None = None
        benchmark_start = time.perf_counter()
        timeout_status: str | None = None
        request_timeout = self.timeout_policy.request_timeout_seconds

        while True:
            attempt += 1
            elapsed = time.perf_counter() - benchmark_start
            if elapsed > request_timeout:
                timeout_status = "request"
                last_exc = TimeoutError(f"Request timeout after {elapsed:.1f}s")
                break

            try:
                response = provider.chat(model, messages, **kwargs)
                break
            except Exception as exc:
                last_exc = exc
                timeout_status = None
                if isinstance(exc, TimeoutError):
                    timeout_status = "request"
                elif isinstance(exc, ConnectionError):
                    if "connection" not in self.retry_policy.retryable:
                        break
                else:
                    name = type(exc).__name__.lower()
                    if not any(t in name for t in self.retry_policy.retryable):
                        break

                if attempt > self.retry_policy.retry_count:
                    break
                time.sleep(self.retry_policy.backoff_factor * (2 ** (attempt - 1)))

        if response is None:
            result = BenchmarkResult(
                model=model,
                provider=ProviderType(provider_name),
                scores=[],
                details={"error": str(last_exc), "error_type": type(last_exc).__name__ if last_exc else "unknown"},
                metadata={"timestamp": datetime.now(timezone.utc).isoformat(), "status": "error", "latency_ms": 0.0},
                retry_count=attempt - 1,
                timeout_status=timeout_status,
            )
            result.calculate_overall()
            self._record_retry_health(provider_name, attempt - 1, result, False)
            if _fallback_depth == 0:
                plan = self.apply_policy(
                    {
                        "provider": provider_name,
                        "model": model,
                        "fallback_providers": self.config.routing.get("fallback_chain", []),
                    }
                )
                for fb_provider in plan.get("fallback_providers", []):
                    if fb_provider == provider_name:
                        continue
                    try:
                        fb = self._get_strategy(PluginCategory.STRATEGY, "execution_policy")
                        if fb is not None:
                            ep = fb()
                            if ep.is_circuit_open(fb_provider):
                                continue
                    except Exception:
                        pass
                    try:
                        return self.run_benchmark(fb_provider, model, benchmark_name_enum, messages, _fallback_depth=1, **kwargs)
                    except Exception:
                        continue
            return result

        try:
            benchmark = benchmark_cls()
            result = benchmark.run(response, prompt=prompt_meta, **kwargs)
            if not isinstance(result, BenchmarkResult):
                raise TypeError("benchmark.run() must return BenchmarkResult")
        except Exception as exc:
            logger.error("Benchmark '%s' failed for model '%s': %s", benchmark_name_enum.value, model, exc)
            result = BenchmarkResult(
                model=model,
                provider=ProviderType(provider_name),
                scores=[],
                details={"error": str(exc), "error_type": type(exc).__name__},
                metadata={"timestamp": datetime.now(timezone.utc).isoformat(), "status": "error"},
            )
            result.calculate_overall()
            self._populate_metadata(result, response, benchmark_start, benchmark_name_enum)
            result.retry_count = attempt - 1
            result.timeout_status = timeout_status
            self._record_retry_health(provider_name, result.retry_count, result, False)
            return result

        result.model = model
        result.provider = ProviderType(provider_name)
        result.metadata.setdefault("status", "success")

        weight = self.config.weight(benchmark_name_enum)
        score = Score(
            benchmark=benchmark_name_enum,
            raw=result.details.get("raw_score", 0.0),
            normalized=result.details.get("normalized", 0.0),
            weight=weight,
        )
        result.scores = [score]
        self._populate_metadata(result, response, benchmark_start, benchmark_name_enum)
        result.retry_count = attempt - 1
        result.timeout_status = timeout_status
        self._record_retry_health(provider_name, result.retry_count, result, True)
        result.calculate_overall()
        return result

    def generate_reports(self, results: list[BenchmarkResult], out_dir: Path, formats: list[str] | None = None, *, runs: list[list[BenchmarkResult]] | None = None) -> dict[str, Path]:
        formats = formats or ["json", "md", "csv"]
        out_dir.mkdir(parents=True, exist_ok=True)
        produced: dict[str, Path] = {}
        for fmt in formats:
            reporter_cls = self.plugins.get(PluginCategory.REPORTER, fmt)
            if reporter_cls is None:
                logger.warning("Reporter plugin not found: %s", fmt)
                continue
            reporter = reporter_cls()
            path = out_dir / f"results.{fmt}"
            kwargs: dict[str, Any] = {"runs": runs}
            if fmt == "cost":
                kwargs["price_lookup"] = lambda provider, model: self.config.model_cost(provider, model)
            reporter.generate(results, path, **kwargs)
            produced[fmt] = path
        return produced

    def cross_provider_benchmark(self, providers: list[str], models: dict[str, list[str]]) -> dict[str, Any]:
        from aibenchmark.app.cross_provider import CrossProviderBenchmark
        bench = CrossProviderBenchmark()
        return bench.compare_providers(providers, models)

    def run_parallel(self, providers: list[str], model: str, benchmark_names: list[str], messages: list[dict[str, Any]]) -> list[BenchmarkResult]:
        from aibenchmark.app.parallel_executor import ParallelExecutor

        parallel_cfg = self.config.routing.get("parallel", {})
        if not parallel_cfg.get("enabled", False):
            raise ConfigError("Parallel execution is disabled in configuration.")
        max_workers = int(parallel_cfg.get("max_workers", 4))
        executor = ParallelExecutor(max_workers=max_workers)

        def job(provider_name: str, benchmark_name: str) -> BenchmarkResult:
            try:
                return self.run_benchmark(provider_name, model, benchmark_name, messages)
            except Exception as exc:
                logger.debug("Parallel job failed for %s/%s: %s", provider_name, benchmark_name, exc)
                return BenchmarkResult(
                    model=model,
                    provider=ProviderType(provider_name),
                    scores=[],
                    details={"error": str(exc), "error_type": type(exc).__name__},
                    metadata={"timestamp": datetime.now(timezone.utc).isoformat(), "status": "error"},
                    retry_count=0,
                )

        flat = [(p, b) for p in providers for b in benchmark_names]
        return executor.map(job, *zip(*flat)) if flat else []


class CostEstimator:
    @staticmethod
    def estimate(prompt_tokens: int, completion_tokens: int, prompt_price_per_1k: float, completion_price_per_1k: float) -> float:
        return (prompt_tokens / 1000.0) * prompt_price_per_1k + (completion_tokens / 1000.0) * completion_price_per_1k
