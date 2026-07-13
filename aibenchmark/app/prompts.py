from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from aibenchmark.app.models import BenchmarkName

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class PromptSet:
    name: str
    system: str = ""
    user: str = ""
    expected: str | None = None
    metadata: dict[str, Any] | None = None


class PromptLoadError(Exception):
    """Raised when a prompt file cannot be loaded."""


class PromptLoader:
    """Loads prompt definitions from YAML files."""

    def __init__(self, config_dir: Path | None = None) -> None:
        self.config_dir = config_dir or Path(__file__).resolve().parent.parent.parent / "configs"
        self._config = None

    def _get_config(self):
        if self._config is None:
            from aibenchmark.app.config import AppConfig
            try:
                self._config = AppConfig(self.config_dir)
            except Exception as exc:
                logger.debug("Config not available for prompt loading: %s", exc)
                return None
        return self._config

    def load(self, benchmark_name: str | BenchmarkName) -> PromptSet | None:
        """Load the default prompt for a benchmark from configured prompt path.

        Falls back to built-in prompts if config path is missing.
        """
        cfg = self._get_config()
        if cfg is None:
            return None

        path = cfg.prompt_path(benchmark_name)
        if path is None or not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            if isinstance(data, list):
                for entry in data:
                    if not isinstance(entry, dict):
                        continue
                    if entry.get("category", path.stem) == benchmark_name:
                        data = entry
                        break
                else:
                    data = data[0] if data else {}
            return PromptSet(
                name=data.get("name", path.stem),
                system=data.get("system", ""),
                user=data.get("user", ""),
                expected=data.get("expected"),
                metadata=data.get("metadata"),
            )
        except Exception as exc:
            raise PromptLoadError(f"Failed to load prompt {path}: {exc}") from exc
