# API Reference — Sprint 14

**Sprint**: 14
**Release**: v2.1.0
**Date**: 2026-07-17

## Common Headers

- `X-Request-ID`: Echoed on every response.
- `X-Correlation-ID`: Echoed on every response.

## System

### GET /api/v1/system/health

Response 200:
```json
{
  "status": "healthy",
  "version": "2.1.0",
  "timestamp": "2026-07-17T12:00:00Z",
  "provider_count": 0,
  "benchmark_count": 9,
  "authenticated_providers": 0,
  "missing_api_credentials": []
}
```

### GET /api/v1/system/version

Response 200:
```json
{
  "version": "2.1.0",
  "name": "AI-Benchmark",
  "api_version": "v1"
}
```

### GET /api/v1/system/diagnostics

Response 200:
```json
{
  "status": "ok",
  "diagnostics": "=== Startup Diagnostics ===\n..."
}
```

## Providers

### GET /api/v1/providers/

Response 200:
```json
{
  "providers": [
    {"name": "openrouter", "authenticated": false, "model_count": 0, "status": "unknown"}
  ],
  "total": 1
}
```

### GET /api/v1/providers/models

Response 200:
```json
{
  "openrouter": []
}
```

### POST /api/v1/providers/refresh

Request body:
```json
{"provider": "openrouter", "force": false}
```

Response 200:
```json
{"openrouter": []}
```

## Benchmarks

### GET /api/v1/benchmarks/

Response 200:
```json
{
  "benchmarks": [
    {"name": "coding", "category": null, "weight": 1.0}
  ],
  "total": 9
}
```

### POST /api/v1/benchmarks/run

Request body:
```json
{
  "provider_name": "openrouter",
  "model": "gpt-4o-mini",
  "benchmarks": ["coding"],
  "messages": [{"role": "user", "content": "Say hello"}],
  "fallback_enabled": true
}
```

Response 200:
```json
{
  "id": "openrouter:gpt-4o-mini:2026-07-17T12:00:00Z",
  "provider": "openrouter",
  "model": "gpt-4o-mini",
  "overall": 0.0,
  "scores": [],
  "status": "success",
  "timestamp": "2026-07-17T12:00:00Z",
  "latency_ms": null,
  "retry_count": 0
}
```

## Recommendations

### POST /api/v1/recommendations/

Request body:
```json
{"runs": 1, "categories": ["coding"]}
```

Response 200:
```json
{
  "items": [
    {
      "category": "coding",
      "model": "gpt-4o-mini",
      "provider": "openrouter",
      "confidence": 0.8,
      "confidence_label": "high",
      "reasons": [],
      "score": 0.0
    }
  ],
  "generated_at": "",
  "source_runs": 1
}
```

## Routing

### POST /api/v1/routing/

Request body:
```json
{
  "benchmark_name": "coding",
  "provider_name": null,
  "model": null,
  "max_cost": null,
  "prefer_free": false,
  "required_capabilities": []
}
```

Response 200:
```json
{
  "provider": "openrouter",
  "model": "gpt-4o-mini",
  "estimated_cost": 0.0,
  "rationale": "",
  "fallback_providers": [],
  "fallback_models": []
}
```

## Error Responses

All errors return:
```json
{
  "error": "ErrorCode",
  "detail": "Human readable message",
  "request_id": "uuid",
  "correlation_id": "uuid"
}
```

HTTP status codes:
- 400: Bad request / domain error
- 404: Not found
- 422: Validation error
- 500: Internal server error
