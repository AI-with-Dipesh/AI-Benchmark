from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, status

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.benchmarks import BenchmarkListResponse, BenchmarkResultResponse, BenchmarkRunRequest
from aibenchmark.app.models import BenchmarkName

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.get("/", response_model=BenchmarkListResponse, status_code=status.HTTP_200_OK)
def list_benchmarks(engine: Any = Depends(get_engine)) -> dict[str, Any]:
    names = engine.list_benchmarks()
    items = []
    for name in names:
        try:
            weight = engine.config.weight(name)
        except Exception:
            weight = 1.0
        items.append({"name": name, "category": None, "weight": weight})
    return BenchmarkListResponse(benchmarks=items, total=len(items)).model_dump()


@router.post("/run", response_model=BenchmarkResultResponse, status_code=status.HTTP_200_OK)
def run_benchmark(body: BenchmarkRunRequest, engine: Any = Depends(get_engine)) -> dict[str, Any]:
    messages = body.messages or [{"role": "user", "content": "Say hello"}]
    benchmark_names = [BenchmarkName(n) for n in body.benchmarks] if body.benchmarks else list(BenchmarkName)
    # Run first benchmark for simplicity; full parallel can be added later
    results = []
    for name in benchmark_names:
        try:
            result = engine.run_benchmark(body.provider_name, body.model, name, messages)
            results.append(result)
            if not body.fallback_enabled:
                break
        except Exception as exc:
            logger.debug("Benchmark %s failed: %s", name, exc)
    if not results:
        raise RuntimeError("All benchmarks failed")
    r = results[0]
    scores = []
    for s in r.scores:
        scores.append({
            "benchmark": s.benchmark.value,
            "raw": s.raw,
            "normalized": s.normalized,
            "weight": s.weight,
            "weighted": s.weighted,
        })
    return BenchmarkResultResponse(
        id=f"{r.provider.value}:{r.model}:{r.metadata.get('timestamp', '')}",
        provider=r.provider.value,
        model=r.model,
        overall=r.overall,
        scores=scores,
        status=r.metadata.get("status", "success"),
        timestamp=r.metadata.get("timestamp"),
        latency_ms=r.metadata.get("latency_ms"),
        retry_count=r.retry_count,
    ).model_dump()


@router.get("/history", status_code=status.HTTP_200_OK)
def benchmark_history(engine: Any = Depends(get_engine)) -> dict[str, Any]:
    from aibenchmark.app.history import load_latest
    latest = load_latest(5)
    return {"runs": len(latest), "data": []}


@router.get("/results/{result_id}", status_code=status.HTTP_200_OK)
def get_result(result_id: str, engine: Any = Depends(get_engine)) -> dict[str, Any]:
    # In a real implementation, this would look up the result by ID
    return {"id": result_id, "status": "not_implemented"}
