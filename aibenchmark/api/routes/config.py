from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, status

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.config import ConfigPatchRequest, ConfigResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/config", tags=["config"])


@router.get("/", response_model=ConfigResponse, status_code=status.HTTP_200_OK)
def get_config(engine: Any = Depends(get_engine)) -> dict[str, Any]:
    cfg = engine.config
    return ConfigResponse(
        benchmark_version=cfg.benchmark_version,
        providers=cfg.providers,
        weights=cfg.weights,
        routing=cfg.routing,
        timeouts={
            "request": cfg.timeouts.request_timeout_seconds,
            "benchmark": cfg.timeouts.benchmark_timeout_seconds,
            "category": cfg.timeouts.category_timeout_seconds,
            "connect": cfg.timeouts.connect_timeout_seconds,
        },
        retry={
            "retry_count": cfg.retry.retry_count,
            "backoff_factor": cfg.retry.backoff_factor,
            "retryable": list(cfg.retry.retryable),
        },
    ).model_dump()


@router.patch("/", status_code=status.HTTP_200_OK)
def patch_config(body: ConfigPatchRequest, engine: Any = Depends(get_engine)) -> dict[str, Any]:
    # Read-only for v2.1; runtime config mutation deferred to v2.2+
    return {
        "status": "read_only",
        "message": "Runtime config mutation is not supported in v2.1. Edit benchmark.yaml and restart.",
        "requested_changes": body.model_dump(exclude_none=True),
    }
