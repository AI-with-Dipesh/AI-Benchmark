from __future__ import annotations

from pathlib import Path
from typing import Any

from aibenchmark.app.models import BenchmarkResult, PluginCategory
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.provider_registry import ProviderRegistry


@register(PluginCategory.REPORTER, "capabilities")
class CapabilitiesReporter:
    plugin_name = "capabilities"
    plugin_category = "reporter"

    def generate(self, results: list[BenchmarkResult], path: Path, **kwargs: Any) -> None:
        registry = ProviderRegistry()
        lines = ["# Provider Capabilities Report", ""]
        for provider in registry.list_providers():
            caps = registry.capabilities(provider)
            lines.append(f"## {provider}")
            lines.append(f"- Chat: {caps.chat}")
            lines.append(f"- Reasoning: {caps.reasoning}")
            lines.append(f"- Vision: {caps.vision}")
            lines.append(f"- Streaming: {caps.streaming}")
            lines.append(f"- Function Calling: {caps.function_calling}")
            lines.append(f"- JSON Mode: {caps.json_mode}")
            lines.append(f"- Structured Output: {caps.structured_output}")
            lines.append(f"- Embeddings: {caps.embeddings}")
            lines.append(f"- Image Generation: {caps.image_generation}")
            lines.append(f"- Audio: {caps.audio}")
            lines.append(f"- Tool Calling: {caps.tool_calling}")
            lines.append(f"- Long Context: {caps.long_context}")
            lines.append(f"- Context Window: {caps.context_window or 'N/A'}")
            lines.append("")
        path.write_text("\n".join(lines), encoding="utf-8")
