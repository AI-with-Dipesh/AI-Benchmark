# Release Notes — v2.1.0

**Release Date**: 2026-07-17
**Type**: Minor

## Highlights

- Introduced programmatic REST API under `/api/v1`
- Preserved 100% CLI backward compatibility
- Added OpenAPI, Swagger UI, ReDoc

## New Features

- FastAPI integration layer
- System health/version/diagnostics endpoints
- Provider listing and model cache refresh
- Benchmark execution via HTTP
- Recommendations endpoint
- Routing endpoint
- Analytics endpoints
- Report generation endpoint
- Configuration read endpoint
- Structured error handling with request/correlation IDs

## Breaking Changes

None.

## Upgrade Notes

Install new dependencies:
```bash
pip install fastapi uvicorn pydantic-settings
```

Start API server:
```bash
python -m aibenchmark.api.app
# or
uvicorn aibenchmark.api.app:app --host 0.0.0.0 --port 8000
```

CLI usage is unchanged.
