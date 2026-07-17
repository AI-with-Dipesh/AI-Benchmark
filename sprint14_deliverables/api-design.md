# API Design Document — Sprint 14

**Sprint**: 14
**Release**: v2.1.0
**Date**: 2026-07-17

## Overview

Sprint 14 transforms AI-Benchmark from a CLI-only tool into an integration platform by exposing existing capabilities through a production-ready REST API.

## Design Principles

- **No rewrite**: All existing subsystems remain untouched.
- **Service layer reuse**: API endpoints delegate to `BenchEngine`, `ProviderRegistry`, `history`, and `analytics`.
- **Versioned**: All endpoints live under `/api/v1`.
- **Stable contracts**: Request/response schemas are Pydantic models.
- **Backward compatible**: CLI unchanged.

## Architecture

```
aibenchmark/api/
  app.py           - FastAPI app factory, CORS, middleware
  deps.py          - Shared singletons: get_engine(), get_registry()
  errors.py        - Structured exception handlers
  schemas/         - Pydantic request/response schemas
  routes/
    system.py      - /api/v1/system/*
    providers.py   - /api/v1/providers/*
    benchmarks.py  - /api/v1/benchmarks/*
    recommendations.py - /api/v1/recommendations/*
    routing.py     - /api/v1/routing/*
    analytics.py   - /api/v1/analytics/*
    reports.py     - /api/v1/reports/*
    config.py      - /api/v1/config/*
```

## API Features

- OpenAPI 3.1 schema at `/openapi.json`
- Swagger UI at `/docs`
- ReDoc at `/redoc`
- Request/Correlation IDs via `X-Request-ID`/`X-Correlation-ID` headers
- CORS enabled
- Structured error responses with `ErrorResponse` schema
- Validation via Pydantic request bodies

## Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/api/v1/system/health` | Health check |
| GET | `/api/v1/system/version` | Version metadata |
| GET | `/api/v1/system/diagnostics` | Engine diagnostics |
| GET | `/api/v1/providers/` | List providers |
| GET | `/api/v1/providers/models` | List all models |
| POST | `/api/v1/providers/refresh` | Refresh model cache |
| GET | `/api/v1/benchmarks/` | List benchmarks |
| POST | `/api/v1/benchmarks/run` | Execute benchmark |
| GET | `/api/v1/benchmarks/history` | Recent history |
| GET | `/api/v1/benchmarks/results/{id}` | Get result by ID |
| POST | `/api/v1/recommendations/` | Generate recommendations |
| POST | `/api/v1/routing/` | Route benchmark to model/provider |
| GET | `/api/v1/analytics/leaderboard` | Category leaderboard |
| GET | `/api/v1/analytics/trends` | Cross-run trends |
| GET | `/api/v1/analytics/history` | History summary |
| POST | `/api/v1/reports/generate` | Generate reports |
| GET | `/api/v1/reports/{id}` | Get report metadata |
| GET | `/api/v1/config/` | Read current config |
| PATCH | `/api/v1/config/` | Partial config update (read-only in v2.1) |

## Non-Functional Requirements

- **Startup**: Engine is singleton-backed; first request initializes.
- **Concurrency**: FastAPI/Starlette async; sync business logic runs in threadpool.
- **Extensibility**: Router-based organization eases future expansion.
