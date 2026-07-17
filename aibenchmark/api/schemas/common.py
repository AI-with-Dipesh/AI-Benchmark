from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "healthy"
    version: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now())


class VersionResponse(BaseModel):
    version: str
    name: str = "AI-Benchmark"
    api_version: str = "v1"


class ErrorResponse(BaseModel):
    error: str
    detail: str
    request_id: str | None = None
    correlation_id: str | None = None


class ProviderSummary(BaseModel):
    name: str
    authenticated: bool
    model_count: int = 0
    status: str = "unknown"


class BenchmarkSummary(BaseModel):
    name: str
    category: str | None = None
    weight: float = 1.0


class RecommendationItem(BaseModel):
    category: str
    model: str
    provider: str
    confidence: float
    confidence_label: str
    reasons: list[str] = Field(default_factory=list)
    score: float = 0.0


class RoutingRequest(BaseModel):
    benchmark_name: str
    provider_name: str | None = None
    model: str | None = None
    max_cost: float | None = None
    prefer_free: bool = False
    required_capabilities: list[str] = Field(default_factory=list)


class RoutingResponse(BaseModel):
    provider: str
    model: str
    estimated_cost: float | None = None
    rationale: str = ""
    fallback_providers: list[str] = Field(default_factory=list)
    fallback_models: list[str] = Field(default_factory=list)


class LeaderboardEntry(BaseModel):
    rank: int
    model: str
    provider: str
    overall: float
    category_scores: dict[str, float] = Field(default_factory=dict)


class TrendPoint(BaseModel):
    timestamp: str
    model: str
    provider: str
    overall: float
    benchmark_count: int = 0
