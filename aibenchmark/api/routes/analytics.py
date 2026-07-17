from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.analytics import LeaderboardResponse, TrendResponse

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/leaderboard", response_model=LeaderboardResponse, status_code=status.HTTP_200_OK)
def leaderboard(engine: Any = Depends(get_engine)) -> dict[str, Any]:
    from aibenchmark.app.history import load_latest
    from aibenchmark.app.analytics import build_leaderboard

    latest = load_latest(1)
    if not latest:
        return LeaderboardResponse(entries=[], generated_at="").model_dump()
    results = latest[0]
    rows = build_leaderboard(results)
    entries = []
    for row in rows[:20]:
        entries.append({
            "rank": row.rank,
            "model": row.model,
            "provider": row.provider,
            "overall": row.overall,
            "category_scores": getattr(row, "category_scores", {}),
        })
    return LeaderboardResponse(entries=entries, generated_at="", runs_analyzed=len(latest)).model_dump()


@router.get("/trends", response_model=TrendResponse, status_code=status.HTTP_200_OK)
def trends(engine: Any = Depends(get_engine)) -> dict[str, Any]:
    from aibenchmark.app.history import load_latest
    from aibenchmark.app.analytics import build_leaderboard

    latest = load_latest(5)
    points = []
    for run_idx, run in enumerate(latest):
        for r in run:
            points.append({
                "timestamp": r.metadata.get("timestamp", ""),
                "model": r.model,
                "provider": r.provider.value,
                "overall": r.overall,
                "benchmark_count": len(r.scores),
            })
    return TrendResponse(trends=points, generated_at="", runs_analyzed=len(latest)).model_dump()


@router.get("/history", status_code=status.HTTP_200_OK)
def history(engine: Any = Depends(get_engine)) -> dict[str, Any]:
    from aibenchmark.app.history import load_latest
    latest = load_latest(10)
    return {"runs": len(latest), "data": []}
