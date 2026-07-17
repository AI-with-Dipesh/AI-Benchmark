from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.common import RoutingRequest, RoutingResponse

router = APIRouter(prefix="/routing", tags=["routing"])


@router.post("/", response_model=RoutingResponse, status_code=status.HTTP_200_OK)
def route(body: RoutingRequest, engine: Any = Depends(get_engine)) -> dict[str, Any]:
    plan = engine.select_model({
        "benchmark_name": body.benchmark_name,
        "provider_name": body.provider_name,
        "model": body.model,
        "max_cost": body.max_cost,
        "prefer_free": body.prefer_free,
        "required_capabilities": body.required_capabilities,
    })
    return RoutingResponse(
        provider=plan.get("provider", ""),
        model=plan.get("model", ""),
        estimated_cost=plan.get("estimated_cost"),
        rationale=plan.get("rationale", ""),
        fallback_providers=plan.get("fallback_providers", []),
        fallback_models=plan.get("fallback_models", []),
    ).model_dump()
