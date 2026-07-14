from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any

from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.provider_registry import ProviderRegistry


def _model_entry(provider_name: str, model_id: str, api_base: str, api_key: str) -> dict[str, Any]:
    return {
        "model_name": f"{provider_name}/{model_id}",
        "litellm_params": {
            "model": model_id,
            "litellm_provider": provider_name,
            "api_base": api_base,
            "api_key": api_key,
        },
        "model_info": {
            "supported_modalities": ["text"],
        },
    }


@register(PluginCategory.REPORTER, "litellm_config")
class LiteLLMConfigReporter:
    plugin_name = "litellm_config"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: object) -> None:
        registry = ProviderRegistry()
        data: dict[str, Any] = {"model_list": []}
        for provider_name in registry.list_providers():
            try:
                cfg = registry.metadata(provider_name)
                models = registry.list_models(provider_name)
            except Exception:
                continue
            api_base = cfg.get("endpoint", "")
            api_key_env = cfg.get("api_key_env", "")
            api_key = f"${{{api_key_env}}}" if api_key_env else cfg.get("api_key", "")
            for model_id in models:
                data["model_list"].append(_model_entry(provider_name, model_id, api_base, api_key))
        path.write_text(yaml.safe_dump(data, sort_keys=False, default_flow_style=False))
