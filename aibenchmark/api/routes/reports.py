from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status

from aibenchmark.api.deps import get_engine
from aibenchmark.api.schemas.reports import ReportGenerateRequest, ReportResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("/generate", response_model=ReportResponse, status_code=status.HTTP_200_OK)
def generate_reports(body: ReportGenerateRequest, engine: Any = Depends(get_engine)) -> dict[str, Any]:
    from pathlib import Path
    from aibenchmark.app.history import load_latest

    out_dir = Path(body.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    latest = load_latest(1)
    results = latest[0] if latest else []
    produced = engine.generate_reports(results, out_dir, formats=body.formats)
    files = {fmt: str(path) for fmt, path in produced.items()}
    return ReportResponse(
        id=f"report-{datetime.now(timezone.utc).isoformat()}",
        formats=list(files.keys()),
        files=files,
        created_at=datetime.now(timezone.utc).isoformat(),
    ).model_dump()


@router.get("/{report_id}", status_code=status.HTTP_200_OK)
def get_report(report_id: str) -> dict[str, Any]:
    return {"id": report_id, "status": "not_implemented"}
