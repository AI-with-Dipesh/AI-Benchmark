from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

from aibenchmark.api.deps import request_id_middleware
from aibenchmark.api.errors import register_exception_handlers
from aibenchmark.api.routes.analytics import router as analytics_router
from aibenchmark.api.routes.benchmarks import router as benchmarks_router
from aibenchmark.api.routes.config import router as config_router
from aibenchmark.api.routes.providers import router as providers_router
from aibenchmark.api.routes.recommendations import router as recommendations_router
from aibenchmark.api.routes.reports import router as reports_router
from aibenchmark.api.routes.routing import router as routing_router
from aibenchmark.api.routes.system import router as system_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting AI-Benchmark API v2.1.0")
    yield
    logger.info("Shutting down AI-Benchmark API")


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI-Benchmark API",
        description="Programmatic API for LLM benchmarking, routing, and analytics",
        version="2.1.0",
        lifespan=lifespan,
        license_info={"name": "MIT", "url": "https://opensource.org/licenses/MIT"},
        contact={"name": "AI-Benchmark Team"},
    )

    # Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.middleware("http")(request_id_middleware)

    register_exception_handlers(app)

    # Versioned API using include_router so OpenAPI schema is populated
    app.include_router(system_router, prefix="/api/v1")
    app.include_router(providers_router, prefix="/api/v1")
    app.include_router(benchmarks_router, prefix="/api/v1")
    app.include_router(recommendations_router, prefix="/api/v1")
    app.include_router(routing_router, prefix="/api/v1")
    app.include_router(analytics_router, prefix="/api/v1")
    app.include_router(reports_router, prefix="/api/v1")
    app.include_router(config_router, prefix="/api/v1")

    return app


app = create_app()
