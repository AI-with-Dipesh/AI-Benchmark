from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConfigResponse(BaseModel):
    benchmark_version: str
    providers: dict[str, Any] = Field(default_factory=dict)
    weights: dict[str, float] = Field(default_factory=dict)
    routing: dict[str, Any] = Field(default_factory=dict)
    timeouts: dict[str, float] | None = None
    retry: dict[str, Any] | None = None


class ConfigPatchRequest(BaseModel):
    weights: dict[str, float] | None = None
    routing: dict[str, Any] | None = None
    run_defaults: dict[str, Any] | None = None
