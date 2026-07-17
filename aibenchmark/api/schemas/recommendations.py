from __future__ import annotations

from pydantic import BaseModel, Field

from aibenchmark.api.schemas.common import RecommendationItem


class RecommendationRequest(BaseModel):
    runs: int = 1
    categories: list[str] | None = None


class RecommendationResponse(BaseModel):
    items: list[RecommendationItem]
    generated_at: str
    source_runs: int = 0
