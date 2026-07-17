# Integration Guide — Sprint 14

**Sprint**: 14
**Release**: v2.1.0
**Date**: 2026-07-17

## Quickstart

Start the API server:

```bash
pip install fastapi uvicorn pydantic-settings
python -m aibenchmark.api.app
# or
uvicorn aibenchmark.api.app:app --host 0.0.0.0 --port 8000
```

Access interactive docs:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
- OpenAPI JSON: http://localhost:8000/openapi.json

## Base URL

```
/api/v1
```

## Authentication

No authentication in v2.1. Planned for v2.2.

## Running a Benchmark

```bash
curl -X POST http://localhost:8000/api/v1/benchmarks/run   -H "Content-Type: application/json"   -d '{"provider_name":"openrouter","model":"gpt-4o-mini","benchmarks":["coding"]}'
```

## Routing

```bash
curl -X POST http://localhost:8000/api/v1/routing/   -H "Content-Type: application/json"   -d '{"benchmark_name":"coding","prefer_free":false}'
```

## Recommendations

```bash
curl -X POST http://localhost:8000/api/v1/recommendations/   -H "Content-Type: application/json"   -d '{"runs":1}'
```

## Reports

```bash
curl -X POST http://localhost:8000/api/v1/reports/generate   -H "Content-Type: application/json"   -d '{"formats":["json","md"]}'
```

## Python Client Example

```python
from fastapi.testclient import TestClient
from aibenchmark.api.app import create_app

app = create_app()
client = TestClient(app)

health = client.get("/api/v1/system/health").json()
print(health)
```

## CI/CD Integration

The API can replace direct `BenchEngine()` instantiation in automation pipelines, providing:
- Network-accessible execution
- Standard HTTP auth hooks future-ready
- Observability via request/correlation IDs
- Stable OpenAPI contract
