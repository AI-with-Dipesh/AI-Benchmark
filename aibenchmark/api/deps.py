from __future__ import annotations

import uuid
from typing import AsyncGenerator

from fastapi import Request

from aibenchmark.app.engine import BenchEngine
from aibenchmark.app.provider_registry import ProviderRegistry

_engine: BenchEngine | None = None
_registry: ProviderRegistry | None = None


def get_engine() -> BenchEngine:
    global _engine
    if _engine is None:
        _engine = BenchEngine()
    return _engine


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    correlation_id = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Correlation-ID"] = correlation_id
    return response
