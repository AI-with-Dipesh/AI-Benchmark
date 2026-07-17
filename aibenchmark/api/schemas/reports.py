from __future__ import annotations

from pydantic import BaseModel, Field


class ReportGenerateRequest(BaseModel):
    result_ids: list[str] | None = None
    formats: list[str] = Field(default_factory=lambda: ["json", "md", "csv"])
    out_dir: str = "reports"


class ReportResponse(BaseModel):
    id: str
    formats: list[str] = Field(default_factory=list)
    files: dict[str, str] = Field(default_factory=dict)
    created_at: str
