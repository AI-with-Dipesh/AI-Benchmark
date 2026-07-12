from __future__ import annotations

import time
from typing import Any

from aibenchmark.interfaces.provider import BaseProvider
from aibenchmark.app.models import ProviderType, ResponseObject, PluginCategory
from aibenchmark.app.plugin.registry import register


@register(PluginCategory.PROVIDER, "ollama")
class OllamaProvider(BaseProvider):
    provider_type = ProviderType.OLLAMA
    plugin_name = "ollama"

    def __init__(self, api_key: str = "", base_url: str = "http://localhost:11434/v1", **kwargs):
        super().__init__(api_key, base_url, **kwargs)

    def connect(self) -> None:
        import httpx
        with httpx.Client(timeout=5) as client:
            r = client.get(self.base_url.replace("/v1", ""))
            r.raise_for_status()

    def list_models(self) -> list[str]:
        import httpx
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(self.base_url.replace("/v1", "") + "/api/tags")
                if r.status_code == 200:
                    return [m["name"] for m in r.json().get("models", [])]
        except Exception:
            pass
        return []

    def chat(self, model: str, messages: list[dict[str, str]], **kwargs) -> ResponseObject:
        start = time.perf_counter()
        import httpx
        with httpx.Client(timeout=120) as client:
            r = client.post(
                f"{self.base_url}/chat/completions",
                json={"model": model, "messages": messages, "stream": False, **kwargs},
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
