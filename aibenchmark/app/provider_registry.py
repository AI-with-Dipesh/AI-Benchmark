from __future__ import annotations

import importlib
import logging
import time
from typing import TYPE_CHECKING, Any, Type

from aibenchmark.app.models import PluginCategory, ProviderCapabilities, ProviderHealth
from aibenchmark.app.plugin.registry import get_manager
from aibenchmark.app.provider_capabilities import ProviderCapabilityDetector
from aibenchmark.app.provider_health import get_health_tracker

if TYPE_CHECKING:
    from aibenchmark.app.certification import ProviderCertificationReport
from aibenchmark.app.provider_cache import ModelCache
from pathlib import Path

logger = logging.getLogger(__name__)


class ProviderRegistry:
    def __init__(self, cache_path: str | Path | None = None, cache_ttl: int = 3600) -> None:
        import aibenchmark.plugins  # noqa: F401 - trigger built-in registration
        self._manager = get_manager()
        self.capability_detector = ProviderCapabilityDetector()
        self.health_tracker = get_health_tracker()
        self.model_cache = ModelCache(Path(cache_path) if cache_path else None, ttl=cache_ttl)

    def list_providers(self) -> list[str]:
        return self._manager.list_names(PluginCategory.PROVIDER)

    def get_plugin(self, provider_name: str) -> Type[Any] | None:
        return self._manager.get(PluginCategory.PROVIDER, provider_name)

    def instantiate(self, provider_name: str, api_key: str = "", base_url: str = "", **kwargs: Any) -> Any:
        cls = self.get_plugin(provider_name)
        if cls is None:
            raise ValueError(f"Unknown provider: {provider_name}")
        return cls(api_key=api_key, base_url=base_url, **kwargs)

    def capabilities(self, provider_name: str) -> ProviderCapabilities:
        plugin = self.get_plugin(provider_name)
        if plugin is not None:
            try:
                instance = self._safe_init(plugin)
                if hasattr(instance, "capabilities"):
                    caps = instance.capabilities()
                    if isinstance(caps, ProviderCapabilities):
                        return caps
            except Exception:
                pass
        return self.capability_detector.detect(provider_name)

    def health(self, provider_name: str) -> ProviderHealth:
        plugin = self.get_plugin(provider_name)
        if plugin is None:
            raise ValueError(f"Unknown provider: {provider_name}")
        try:
            instance = self._safe_init(plugin)
            start = time.perf_counter()
            instance.connect()
            latency = (time.perf_counter() - start) * 1000
            return self.health_tracker.record(provider_name, latency, True)
        except TimeoutError:
            return self.health_tracker.record(provider_name, 0.0, False, is_timeout=True)
        except Exception as exc:
            logger.debug("Health check for %s failed: %s", provider_name, exc)
            return self.health_tracker.record(provider_name, 0.0, False)

    def all_health(self) -> dict[str, ProviderHealth]:
        result: dict[str, ProviderHealth] = {}
        for name in self.list_providers():
            result[name] = self.health(name)
        return result

    def metadata(self, provider_name: str) -> dict[str, Any]:
        plugin = self.get_plugin(provider_name)
        if plugin is None:
            raise ValueError(f"Unknown provider: {provider_name}")
        try:
            instance = self._safe_init(plugin)
            meta = instance.metadata()
            if hasattr(meta, "__dict__"):
                return dict(meta.__dict__)
            return dict(meta)
        except Exception as exc:
            logger.debug("Metadata for %s failed: %s", provider_name, exc)
            return {"provider_name": provider_name, "error": str(exc)}

    def list_models(self, provider_name: str) -> list[str]:
        plugin = self.get_plugin(provider_name)
        if plugin is None:
            raise ValueError(f"Unknown provider: {provider_name}")
        live_models: list[str] = []
        try:
            instance = self._safe_init(plugin)
            models = instance.list_models()
            if isinstance(models, list):
                live_models = [str(m) for m in models]
            else:
                live_models = [str(m) for m in models]
        except Exception as exc:
            logger.debug("list_models for %s failed: %s", provider_name, exc)

        if live_models:
            # Live success: update cache, return live results
            self.model_cache.set(provider_name, live_models)
            return live_models

        # Live failed: fall back to cache
        cached = self.model_cache.get(provider_name)
        if cached:
            logger.info("Using cached model list for %s (%d models)", provider_name, len(cached))
            return cached

        return []

    def validate_configuration(self, provider_name: str) -> dict[str, Any]:
        plugin = self.get_plugin(provider_name)
        if plugin is None:
            raise ValueError(f"Unknown provider: {provider_name}")
        try:
            instance = self._safe_init(plugin)
            result = instance.validate_configuration()
            if isinstance(result, dict):
                return result
            return {"valid": False, "issues": [str(result)]}
        except Exception as exc:
            return {"valid": False, "issues": [str(exc)]}

    @staticmethod
    def _safe_init(cls: Type[Any]) -> Any:
        return cls(api_key="", base_url="")

    @staticmethod
    def load_provider(provider_name: str) -> Type[Any]:
        mod_name = f"aibenchmark.plugins.providers.{provider_name}"
        try:
            mod = importlib.import_module(mod_name)
            candidates = []
            for attr_name in dir(mod):
                attr = getattr(mod, attr_name)
                if isinstance(attr, type):
                    pcat = getattr(attr, "plugin_category", "")
                    pname = getattr(attr, "plugin_name", attr.__name__)
                    if pcat == "provider" and pname == provider_name and attr_name != "BaseProvider":
                        candidates.append(attr)
            if not candidates:
                raise ImportError(f"No provider class found in '{mod_name}'")
            return candidates[0]
        except ImportError:
            raise
        except Exception as exc:
            raise ImportError(f"Cannot load provider plugin '{provider_name}': {exc}") from exc

    def compare_providers(self, providers: list[str], models: dict[str, list[str]]) -> dict[str, Any]:
        from aibenchmark.app.cross_provider import CrossProviderBenchmark
        bench = CrossProviderBenchmark()
        return bench.compare_providers(providers, models)

    def validate_all(self) -> dict[str, dict[str, Any]]:
        result: dict[str, dict[str, Any]] = {}
        for name in self.list_providers():
            result[name] = self.validate_configuration(name)
        return result

    def certify(self, provider_name: str) -> ProviderCertificationReport:
        from aibenchmark.app.certification import ProviderCertifier
        certifier = ProviderCertifier()
        return certifier.certify(provider_name)
