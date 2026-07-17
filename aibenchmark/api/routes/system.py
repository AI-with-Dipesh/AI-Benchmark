from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.common import HealthResponse, VersionResponse

router = APIRouter(prefix="/system", tags=["system"])


class DetailedHealthResponse(HealthResponse):
    provider_count: int = 0
    benchmark_count: int = 0
    authenticated_providers: int = 0
    missing_api_credentials: list[str] = []


@router.get("/health", response_model=DetailedHealthResponse, status_code=status.HTTP_200_OK)
def health() -> dict[str, Any]:
    return DetailedHealthResponse(
        status="healthy",
        version="2.1.0",
        timestamp=datetime.now(timezone.utc),
    ).model_dump()


@router.get("/version", response_model=VersionResponse, status_code=status.HTTP_200_OK)
def version() -> dict[str, Any]:
    return VersionResponse(version="2.1.0").model_dump()


@router.get("/diagnostics", status_code=status.HTTP_200_OK)
def diagnostics(engine: Any = Depends(get_engine)) -> dict[str, Any]:
    try:
        summary = engine.diagnostics_summary()
        # Parse the diagnostics summary into a structured format
        return {
            "status": "ok",
            "diagnostics": summary,
        }
    except Exception as exc:
        return {
            "status": "error",
            "error": str(exc),
        }
