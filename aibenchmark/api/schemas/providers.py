from __future__ import annotations

from pydantic import BaseModel, Field

from aibenchmark.api.schemas.common import ProviderSummary


class ProviderListResponse(BaseModel):
    providers: list[ProviderSummary]
    total: int


class ModelListResponse(BaseModel):
    provider: str
    models: list[str]
    cached: bool = False
    source: str = "live"


class ProviderRefreshRequest(BaseModel):
    provider: str | None = None
    force: bool = False
