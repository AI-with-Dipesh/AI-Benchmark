from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from aibenchmark.app.models import BenchmarkName, TimeoutPolicy, RetryPolicy

logger = logging.getLogger(__name__)


class ConfigError(Exception):
    """Raised when configuration is missing or invalid."""


class AppConfig:
    """Loads and validates benchmark suite configuration."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or Path(__file__).resolve().parent.parent.parent / "configs"
        self.providers: dict[str, Any] = {}
        self.weights: dict[str, float] = {}
        self.default_prompts: dict[str, str] = {}
        self.run_defaults: dict[str, Any] = {}
        self.retry: RetryPolicy = RetryPolicy()
        self.timeouts: TimeoutPolicy = TimeoutPolicy()
        self.cost: dict[str, Any] = {}
        self.prompt_versions: dict[str, str] = {}
        self.benchmark_version: str = "0.4.0"
        self._load()

    def _load(self) -> None:
        providers_path = self.config_dir / "providers.yaml"
        benchmark_path = self.config_dir / "benchmark.yaml"

        if not providers_path.exists():
            raise ConfigError(f"Missing providers config: {providers_path}")
        if not benchmark_path.exists():
            raise ConfigError(f"Missing benchmark config: {benchmark_path}")

        try:
            with providers_path.open("r", encoding="utf-8") as f:
                self.providers = yaml.safe_load(f) or {}
        except Exception as exc:
            raise ConfigError(f"Invalid providers config {providers_path}: {exc}") from exc

        try:
            with benchmark_path.open("r", encoding="utf-8") as f:
                benchmark_cfg = yaml.safe_load(f) or {}
            self.weights = benchmark_cfg.get("weights", {})
            self.default_prompts = benchmark_cfg.get("default_prompts", {})
            self.run_defaults = benchmark_cfg.get("run_defaults", {})
            self.prompt_versions = benchmark_cfg.get("prompt_versions", {})
            self.benchmark_version = str(benchmark_cfg.get("benchmark_version", self.benchmark_version))
            self.cost = benchmark_cfg.get("cost", {})
            retry_cfg = benchmark_cfg.get("retry", {})
            if retry_cfg:
                self.retry = RetryPolicy(
                    retry_count=int(retry_cfg.get("retry_count", self.retry.retry_count)),
                    backoff_factor=float(retry_cfg.get("backoff_factor", self.retry.backoff_factor)),
                    retryable=tuple(retry_cfg.get("retryable", list(self.retry.retryable))),
                )
            timeout_cfg = benchmark_cfg.get("timeouts", {})
            if timeout_cfg:
                self.timeouts = TimeoutPolicy(
                    request_timeout_seconds=float(timeout_cfg.get("request", getattr(self.timeouts, "request_timeout_seconds", 60.0))),
                    benchmark_timeout_seconds=float(timeout_cfg.get("benchmark", getattr(self.timeouts, "benchmark_timeout_seconds", 240.0))),
                    category_timeout_seconds=float(timeout_cfg.get("category", getattr(self.timeouts, "category_timeout_seconds", 120.0))),
                    connect_timeout_seconds=float(timeout_cfg.get("connect", getattr(self.timeouts, "connect_timeout_seconds", 10.0))),
                )
        except Exception as exc:
            raise ConfigError(f"Invalid benchmark config {benchmark_path}: {exc}") from exc

        self._resolve_api_keys()

    def _resolve_api_keys(self) -> None:
        """Resolve API keys from environment variables referenced in provider configs.

        Validation/warnings are intentionally deferred to provider initialization
        so unused providers do not produce noise.
        """
        for provider_name, cfg in self.providers.items():
            if not isinstance(cfg, dict):
                continue
            if provider_name == "defaults":
                continue
            api_key_env = cfg.get("api_key_env")
            if api_key_env:
                api_key = os.environ.get(api_key_env, "").strip()
                cfg["api_key"] = api_key
            else:
                cfg["api_key"] = ""

    def provider_config(self, name: str) -> dict[str, Any]:
        if name not in self.providers:
            raise ConfigError(f"Unknown provider in config: {name}")
        return self.providers[name]

    def defaults(self) -> dict[str, Any]:
        defaults = self.providers.get("defaults", {})
        if not isinstance(defaults, dict):
            return {}
        return defaults

    def weight(self, benchmark_name: str | BenchmarkName) -> float:
        key = benchmark_name.value if isinstance(benchmark_name, BenchmarkName) else benchmark_name
        return float(self.weights.get(key, 1.0))

    def prompt_path(self, benchmark_name: str | BenchmarkName) -> Path | None:
        key = benchmark_name.value if isinstance(benchmark_name, BenchmarkName) else benchmark_name
        rel = self.default_prompts.get(key)
        if not rel:
            return None
        inside = self.config_dir / rel
        if inside.exists():
            return inside
        outside = self.config_dir.parent / rel
        return outside if outside.exists() else None

    def prompt_version(self, benchmark_name: str | BenchmarkName) -> str | None:
        key = benchmark_name.value if isinstance(benchmark_name, BenchmarkName) else benchmark_name
        return self.prompt_versions.get(key)

    def model_cost(self, provider: str, model: str) -> tuple[float, float]:
        provider_cfg = self.cost.get(provider, {})
        model_cfg = provider_cfg.get(model, provider_cfg.get("default", {"prompt": 0.0, "completion": 0.0}))
        if not isinstance(model_cfg, dict):
            model_cfg = provider_cfg.get("default", {"prompt": 0.0, "completion": 0.0})
        return float(model_cfg.get("prompt", 0.0)), float(model_cfg.get("completion", 0.0))
