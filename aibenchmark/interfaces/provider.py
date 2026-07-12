from abc import ABC, abstractmethod
from typing import Any

from aibenchmark.app.models import ProviderType, ResponseObject


class BaseProvider(ABC):
    plugin_name: str = ""
    plugin_category: str = "provider"

    def __init__(self, api_key: str, base_url: str | None = None, **kwargs: Any) -> None:
        self.api_key = api_key
        self.base_url = base_url
        self.config = kwargs

    @abstractmethod
    def connect(self) -> None: ...

    @abstractmethod
    def list_models(self) -> list[str]: ...

    @abstractmethod
    def chat(self, model: str, messages: list[dict[str, str]], **kwargs: Any) -> ResponseObject: ...

    def health_check(self) -> bool:
        try:
            self.connect()
            return True
        except Exception:
            return False

    def supports_streaming(self) -> bool:
        return False

    def supports_tools(self) -> bool:
        return True

    def supports_json(self) -> bool:
        return True

    def supports_context_length(self) -> bool:
        return True

    def metadata(self) -> dict[str, Any]:
        return {
            "provider": getattr(self, "provider_type", None),
            "streaming": self.supports_streaming(),
            "tools": self.supports_tools(),
            "json": self.supports_json(),
            "context_length": self.supports_context_length(),
        }
