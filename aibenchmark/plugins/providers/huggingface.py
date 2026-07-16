from __future__ import annotations

import time
from typing import Any

from aibenchmark.interfaces.provider import BaseProvider
from aibenchmark.app.models import ProviderCapabilities, ProviderMetadata, ProviderType, ResponseObject
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.models import PluginCategory


@register(PluginCategory.PROVIDER, "huggingface")
class HuggingFaceProvider(BaseProvider):
    provider_type = ProviderType.HUGGINGFACE
    plugin_name = "huggingface"

    plugin_api_version = "1.0"
    def __init__(self, api_key: str, base_url: str = "https://api-inference.huggingface.co/v1", **kwargs: Any) -> None:
        super().__init__(api_key, base_url, **kwargs)

    def connect(self) -> None:
        import httpx
        with httpx.Client(timeout=10) as client:
            r = client.get(
                "https://api-inference.huggingface.co/v1",
                headers={"Authorization": f"Bearer {self.api_key}"},
            )
            r.raise_for_status()

    def list_models(self) -> list[str]:
        import httpx
        try:
            with httpx.Client(timeout=10) as client:
                r = client.get(
                    "https://huggingface.co/api/models",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                )
                if r.status_code == 200:
                    data = r.json()
                    return [m["id"] for m in data if m.get("pipeline_tag") in ("text-generation", "text2text-generation")]
        except Exception:
            pass
        return []

    def chat(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> ResponseObject:
        start = time.perf_counter()
        import httpx
        with httpx.Client(timeout=120) as client:
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
            context_window=32000,
            max_output_tokens=4096,
        )

    def metadata(self) -> ProviderMetadata:
        caps = self.capabilities()
        return ProviderMetadata(
            provider_name=self.plugin_name,
            provider_version="1.0.0",
            endpoint="https://api-inference.huggingface.co/v1",
            region="us",
            capabilities=caps,
            supported_models=self.list_models(),
            authentication_type="bearer",
            context_window=caps.context_window,
            streaming_support=caps.streaming,
            function_calling_support=False,
            vision_support=False,
            reasoning_support=False,
            embeddings_support=caps.embeddings,
            json_mode_support=caps.json_mode,
        )

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return (prompt_tokens / 1000.0) * 0.0006 + (completion_tokens / 1000.0) * 0.0006

    def validate_configuration(self) -> dict[str, Any]:
        issues = []
        if not self.api_key:
            issues.append("Missing HF_API_KEY")
        if not self.base_url:
            issues.append("Missing base_url")
        return {"valid": len(issues) == 0, "issues": issues}
