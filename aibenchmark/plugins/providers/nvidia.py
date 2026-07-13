from __future__ import annotations

import time
from typing import Any

from aibenchmark.interfaces.provider import BaseProvider
from aibenchmark.app.models import ProviderCapabilities, ProviderMetadata, ProviderType, ResponseObject
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.models import PluginCategory


@register(PluginCategory.PROVIDER, "nvidia")
class NVIDIAProvider(BaseProvider):
    provider_type = ProviderType.NVIDIA
    plugin_name = "nvidia"

    def __init__(self, api_key: str, base_url: str = "https://integrate.api.nvidia.com/v1", **kwargs):
        super().__init__(api_key, base_url, **kwargs)

    def connect(self) -> None:
        import httpx
        with httpx.Client(timeout=10) as client:
            r = client.get(
                "https://integrate.api.nvidia.com/v1/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            r.raise_for_status()

    def list_models(self) -> list[str]:
        import httpx
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(
                    "https://integrate.api.nvidia.com/v1/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    return [m.get("id", "") for m in data.get("data", [])]
        except Exception:
            pass
        return []

    def chat(self, model: str, messages: list[dict[str, str]], **kwargs) -> ResponseObject:
        start = time.perf_counter()
        import httpx
        with httpx.Client(timeout=60) as client:
            r = client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, **kwargs},
            )
            r.raise_for_status()
            data = r.json()
        latency = (time.perf_counter() - start) * 1000
        choice = data.get("choices", [{}])[0]
        content = choice.get("message", {}).get("content", "")
        usage = data.get("usage", {})
        return ResponseObject(
            provider=self.provider_type,
            model=model,
            content=content,
            latency_ms=latency,
            tokens_in=usage.get("prompt_tokens"),
            tokens_out=usage.get("completion_tokens"),
            raw=data,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            chat=True,
            streaming=True,
            json_mode=True,
            context_window=128000,
            max_output_tokens=4096,
        )

    def metadata(self) -> ProviderMetadata:
        caps = self.capabilities()
        return ProviderMetadata(
            provider_name=self.plugin_name,
            provider_version="1.0.0",
            endpoint="https://integrate.api.nvidia.com/v1",
            region="us",
            capabilities=caps,
            supported_models=self.list_models(),
            authentication_type="bearer",
            context_window=caps.context_window,
            streaming_support=caps.streaming,
            function_calling_support=False,
            vision_support=False,
            reasoning_support=True,
            embeddings_support=caps.embeddings,
            json_mode_support=caps.json_mode,
        )

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens / 1000.0) * 0.001 + (completion_tokens / 1000.0) * 0.002

    def validate_configuration(self) -> dict[str, Any]:
        issues = []
        if not self.api_key:
            issues.append("Missing NVIDIA_API_KEY")
        if not self.base_url:
            issues.append("Missing base_url")
        return {"valid": len(issues) == 0, "issues": issues}
