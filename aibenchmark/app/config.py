from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from aibenchmark.app.models import BenchmarkName

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
