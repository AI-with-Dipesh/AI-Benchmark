from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from aibenchmark.app.config import AppConfig, ConfigError
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, PluginCategory, ProviderType, ResponseObject, Score
from aibenchmark.app.plugin.registry import get_manager

logger = logging.getLogger(__name__)


class BenchEngine:
    def __init__(self, config_dir: Path | None = None) -> None:
        import aibenchmark.plugins  # noqa: F401 - trigger built-in plugin registration
        self.plugins = get_manager()
        try:
            self.config = AppConfig(config_dir)
        except ConfigError as exc:
            raise RuntimeError(f"Benchmark configuration failed: {exc}") from exc

    def list_providers(self) -> list[str]:
        return self.plugins.list_names(PluginCategory.PROVIDER)

    def list_benchmarks(self) -> list[str]:
        return self.plugins.list_names(PluginCategory.BENCHMARK)

    def list_reporters(self) -> list[str]:
        return self.plugins.list_names(PluginCategory.REPORTER)

    def _init_provider(self, provider_name: str, **kwargs) -> Any:
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

    def _load_prompt(self, benchmark_name: BenchmarkName) -> dict[str, Any]:
        from aibenchmark.app.prompts import PromptLoader, PromptLoadError
        loader = PromptLoader()
        prompt = loader.load(benchmark_name)
        if prompt is None:
            return {}
        return {"system": prompt.system, "user": prompt.user}

    def run_benchmark(self, provider_name: str, model: str, benchmark_name: BenchmarkName, messages: list[dict], **kwargs) -> BenchmarkResult:
        provider = self._init_provider(provider_name)
        benchmark_cls = self.plugins.get(PluginCategory.BENCHMARK, benchmark_name.value)
        if benchmark_cls is None:
            raise ValueError(f"Unknown benchmark: {benchmark_name}")

        prompt = self._load_prompt(benchmark_name)
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

        try:
            response = provider.chat(model, messages)
        except Exception as exc:
            logger.error("Provider '%s' model '%s' request failed: %s", provider_name, model, exc)
            result = BenchmarkResult(
                model=model,
                provider=ProviderType(provider_name),
                scores=[],
                details={"error": str(exc), "error_type": type(exc).__name__},
                metadata={"timestamp": datetime.now(timezone.utc).isoformat(), "status": "error"},
            )
            result.calculate_overall()
            return result

        benchmark = benchmark_cls()
        result = benchmark.run(response, prompt=prompt_meta, **kwargs)
        result.metadata.setdefault("status", "success")

        weight = self.config.weight(benchmark_name)
        score = Score(
            benchmark=benchmark_name,
            raw=result.details.get("raw_score", 0.0),
            normalized=result.details.get("normalized", 0.0),
            weight=weight,
        )
        result.scores = [score]
        result.model = model
        result.provider = ProviderType(provider_name)
        result.metadata.setdefault("timestamp", datetime.now(timezone.utc).isoformat())
        result.calculate_overall()
        return result

    def generate_reports(self, results: list[BenchmarkResult], out_dir: Path, formats: list[str] | None = None) -> dict[str, Path]:
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
            reporter.generate(results, path)
            produced[fmt] = path
        return produced
