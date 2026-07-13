from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import replace
from typing import Any, Iterator

from aibenchmark.app.models import (
    AuthResult,
    ProviderCapabilities,
    ProviderMetadata,
    ProviderPluginConfig,
    ProviderType,
    RateLimitStatus,
    ResponseObject,
)


class BaseProvider(ABC):
    plugin_name: str = ""
    plugin_category: str = "provider"

    def __init__(self, api_key: str, base_url: str | None = None, **kwargs: Any) -> None:
        self.api_key = api_key
        self.base_url = base_url or ""
        self.config = kwargs

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def list_models(self) -> list[str]: ...

    @abstractmethod
    def chat(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> ResponseObject: ...

    def initialize(self, config: ProviderPluginConfig) -> None:
        self.config.update(config.__dict__)

    def authenticate(self) -> AuthResult:
        provider_name = "unknown"
        provider_type = getattr(self, "provider_type", None)
        if isinstance(provider_type, ProviderType):
            provider_name = provider_type.value
        return AuthResult(
            authenticated=bool(self.api_key),
            provider=provider_name,
            message="Authentication skipped: no specific implementation.",
            credential_valid=bool(self.api_key),
        )

    def health_check(self) -> bool:
        try:
            self.connect()
            return True
        except Exception:
            return False

    def shutdown(self) -> None:
        """Release provider resources. Override if the provider holds persistent connections."""

    def supports(self, capability: str) -> bool:
        try:
            caps = self.capabilities()
            return caps.has(capability)
        except Exception:
            return False

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities()

    def metadata(self) -> ProviderMetadata:
        caps = self.capabilities()
        return ProviderMetadata(
            provider_name=self.plugin_name,
            endpoint=self.base_url or None,
            capabilities=caps,
            streaming_support=caps.streaming,
            function_calling_support=caps.function_calling or caps.tool_calling,
            vision_support=caps.vision,
            reasoning_support=caps.reasoning,
        )

    def estimate_tokens(self, text: str) -> int:
        return max(1, len(text.split()))

    def estimate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        return 0.0

    def validate_configuration(self) -> dict[str, Any]:
        issues: list[str] = []
        if not self.api_key:
            issues.append("Missing API key")
        if not self.base_url:
            issues.append("Missing base_url")
        return {"valid": len(issues) == 0, "issues": issues}

    def supports_streaming(self) -> bool:
        return self.supports("streaming")

    def supports_tools(self) -> bool:
        return self.supports("function_calling") or self.supports("tool_calling")

    def supports_json(self) -> bool:
        return self.supports("json_mode") or self.supports("structured_output")

    def supports_context_length(self) -> bool:
        return self.capabilities().context_window is not None

    def invoke(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> ResponseObject:
        return self.chat(model, messages, **kwargs)

    def stream(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> Iterator[str]:
        response = self.chat(model, messages, **kwargs)
        yield response.content

    @staticmethod
    def _parse_rate_limit(headers: dict[str, str]) -> RateLimitStatus:
        rl = RateLimitStatus()
        for key in ("x-ratelimit-remaining", "x-ratelimit-limit", "x-ratelimit-reset", "retry-after", "x-ms-ratelimit-remaining"):
            val = headers.get(key, "").strip()
            if not val:
                continue
            try:
                if "remaining" in key.lower():
                    rl = replace(rl, remaining=int(val))
                elif "limit" in key.lower():
                    rl = replace(rl, limit=int(val))
                elif "reset" in key.lower():
                    rl = replace(rl, reset_seconds=int(val))
                elif key == "retry-after":
                    rl = replace(rl, retry_after=int(val))
            except ValueError:
                pass
        return rl
