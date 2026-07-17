from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, status

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.common import RecommendationItem
from aibenchmark.api.schemas.recommendations import RecommendationRequest, RecommendationResponse

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.post("/", response_model=RecommendationResponse, status_code=status.HTTP_200_OK)
def generate_recommendations(body: RecommendationRequest, engine: Any = Depends(get_engine)) -> dict[str, Any]:
    from aibenchmark.app.history import load_latest
    from aibenchmark.app.analytics import recommend

    latest = load_latest(body.runs)
    if not latest:
        return RecommendationResponse(items=[], generated_at="").model_dump()
    results = latest[0]
    recommendations = recommend(results)
    items = []
    for rec in recommendations:
        if body.categories and rec.category not in body.categories:
            continue
        items.append(RecommendationItem(
            category=rec.category,
            model=rec.model,
            provider=rec.provider,
            confidence=rec.confidence,
            confidence_label=rec.confidence_label,
            reasons=rec.reasons,
            score=rec.score,
        ))
    return RecommendationResponse(
        items=items,
        generated_at="",
        source_runs=len(latest),
    ).model_dump()
