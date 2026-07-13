from __future__ import annotations

import logging
from typing import Any

from aibenchmark.app.models import ProviderCapabilities, ProviderPluginConfig

logger = logging.getLogger(__name__)

# Known capability mappings for built-in providers
_BUILTIN_CAPABILITIES: dict[str, dict[str, Any]] = {
    "nvidia": {
        "chat": True,
        "streaming": True,
        "json_mode": True,
        "context_window": 128000,
        "max_output_tokens": 4096,
    },
    "openrouter": {
        "chat": True,
        "streaming": True,
        "function_calling": True,
        "tool_calling": True,
        "json_mode": True,
        "structured_output": True,
        "vision": True,
        "context_window": 200000,
        "max_output_tokens": 8192,
    },
    "ollama": {
        "chat": True,
        "streaming": True,
        "function_calling": True,
        "tool_calling": True,
        "long_context": True,
        "context_window": 32768,
        "max_output_tokens": 4096,
    },
    "huggingface": {
        "chat": True,
        "streaming": True,
        "context_window": 32000,
        "max_output_tokens": 4096,
    },
}

class ProviderCapabilityDetector:
    def __init__(self, provider_names: list[str] | None = None) -> None:
        self.providers = provider_names or list(_BUILTIN_CAPABILITIES.keys())

    def detect(self, provider_name: str) -> ProviderCapabilities:
        known = _BUILTIN_CAPABILITIES.get(provider_name, {})
        kwargs: dict[str, Any] = {}
        for key in (
            "chat",
            "reasoning",
            "vision",
            "streaming",
            "function_calling",
            "json_mode",
            "structured_output",
            "embeddings",
            "image_generation",
            "audio",
            "tool_calling",
            "long_context",
        ):
            kwargs[key] = bool(known.get(key, False))
        kwargs["context_window"] = known.get("context_window")
        kwargs["max_output_tokens"] = known.get("max_output_tokens")
        return ProviderCapabilities(**kwargs)

    def detect_from_config(self, provider_config: ProviderPluginConfig) -> ProviderCapabilities:
        caps = self.detect(provider_config.name)
        tags = [t.lower() for t in provider_config.tags]
        if "image-generation" in tags:
            caps = _replace(caps, image_generation=True)
        if "audio" in tags:
            caps = _replace(caps, audio=True)
        if "embeddings" in tags:
            caps = _replace(caps, embeddings=True)
        if "reasoning" in tags:
            caps = _replace(caps, reasoning=True)
        return caps

    def all_capabilities(self) -> dict[str, ProviderCapabilities]:
        return {name: self.detect(name) for name in self.providers}


def _replace(obj: ProviderCapabilities, **updates: Any) -> ProviderCapabilities:
    # frozen dataclass replacement
    return ProviderCapabilities(**(obj.__dict__ | updates))
