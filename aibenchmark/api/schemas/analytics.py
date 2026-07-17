from __future__ import annotations

from pydantic import BaseModel, Field

from aibenchmark.api.schemas.common import LeaderboardEntry, TrendPoint


class LeaderboardResponse(BaseModel):
    entries: list[LeaderboardEntry]
    generated_at: str
    runs_analyzed: int = 0


class TrendResponse(BaseModel):
    trends: list[TrendPoint]
    generated_at: str
    runs_analyzed: int = 0
