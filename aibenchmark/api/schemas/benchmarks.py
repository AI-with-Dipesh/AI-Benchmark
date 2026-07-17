from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from aibenchmark.api.schemas.common import BenchmarkSummary


class BenchmarkListResponse(BaseModel):
    benchmarks: list[BenchmarkSummary]
    total: int


class BenchmarkRunRequest(BaseModel):
    provider_name: str
    model: str
    benchmarks: list[str] | None = None
    messages: list[dict[str, Any]] | None = None
    fallback_enabled: bool = True


class BenchmarkScoreSchema(BaseModel):
    benchmark: str
    raw: float
    normalized: float
    weight: float
    weighted: float


class BenchmarkResultResponse(BaseModel):
    id: str
    provider: str
    model: str
    overall: float
    scores: list[BenchmarkScoreSchema] = Field(default_factory=list)
    status: str = "success"
    timestamp: str | None = None
    latency_ms: float | None = None
    retry_count: int = 0
