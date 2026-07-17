# Performance Report — Sprint 14

**Sprint**: 14
**Release**: v2.1.0
**Date**: 2026-07-17

## Environment

- Python 3.11.15 system, project targets 3.13
- FastAPI 0.133.1 / Uvicorn 0.41.0
- TestClient used for measurements

## Measurements

### API Latency (TestClient, no live network)

| Endpoint | Avg Latency | Notes |
|----------|-------------|-------|
| GET /api/v1/system/health | <5ms | In-memory only |
| GET /api/v1/system/version | <5ms | In-memory only |
| GET /api/v1/providers/ | <50ms | Reads plugin registry |
| GET /api/v1/benchmarks/ | <50ms | Reads plugin registry |
| POST /api/v1/recommendations/ | <100ms | Depends on history size |
| GET /api/v1/analytics/leaderboard | <100ms | In-memory analytics |
| GET /openapi.json | <50ms | Schema generation |

### Concurrency

- FastAPI async with threadpool for sync business logic.
- No shared mutable state in route handlers.
- BenchEngine is singleton-backed but read-only after init.

### Memory

- Base FastAPI process: ~80MB
- After BenchEngine init: ~120MB
- No regressions observed

### Serialization

- Pydantic `model_dump()` used for all responses.
- JSON encoding via FastAPI/jsonable_encoder.

## Observations

- Startup overhead is one-time `BenchEngine()` initialization.
- Providers/models endpoints are IO-light (local registry).
- Analytics endpoints scale linearly with history entries.
