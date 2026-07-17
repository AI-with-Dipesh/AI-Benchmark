from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from aibenchmark.api.deps import get_engine, get_registry
from aibenchmark.api.schemas.common import ProviderSummary
from aibenchmark.api.schemas.providers import ModelListResponse, ProviderListResponse, ProviderRefreshRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/providers", tags=["providers"])


@router.get("/", response_model=ProviderListResponse, status_code=status.HTTP_200_OK)
def list_providers(registry: Any = Depends(get_registry)) -> dict[str, Any]:
    names = registry.list_providers()
    providers = []
    for name in names:
        authenticated = False
        try:
            cfg = registry._safe_init(registry.get_plugin(name)) if registry.get_plugin(name) else None
            # Check if we have an API key configured
            from aibenchmark.app.config import ConfigError
            try:
                engine = get_engine()
                pcfg = engine.config.provider_config(name)
                authenticated = bool(pcfg.get("api_key", ""))
            except (ConfigError, Exception):
                pass
            # Model count from cache or live
            try:
                models = registry.list_models(name)
            except Exception:
                models = []
            providers.append(ProviderSummary(
                name=name,
                authenticated=authenticated,
                model_count=len(models),
            ))
        except Exception as exc:
            logger.debug("Provider summary for %s failed: %s", name, exc)
            providers.append(ProviderSummary(name=name, authenticated=False))
    return ProviderListResponse(providers=providers, total=len(providers)).model_dump()


@router.get("/models", response_model=dict[str, list[str]], status_code=status.HTTP_200_OK)
def list_all_models(registry: Any = Depends(get_registry)) -> dict[str, Any]:
    result: dict[str, list[str]] = {}
    for name in registry.list_providers():
        try:
            result[name] = registry.list_models(name)
        except Exception as exc:
            logger.debug("list_models for %s failed: %s", name, exc)
            result[name] = []
    return result


@router.post("/models/refresh", status_code=status.HTTP_200_OK)
def refresh_models(body: ProviderRefreshRequest, registry: Any = Depends(get_registry)) -> dict[str, Any]:
    if body.provider:
        if body.force:
            registry.model_cache.invalidate(body.provider)
        models = registry.list_models(body.provider)
        return {body.provider: models}
    # Refresh all
    result: dict[str, list[str]] = {}
    for name in registry.list_providers():
        if body.force:
            registry.model_cache.invalidate(name)
        try:
            result[name] = registry.list_models(name)
        except Exception:
            result[name] = []
    return result
