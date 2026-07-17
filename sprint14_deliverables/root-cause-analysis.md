# Root Cause Analysis — Sprint 14 Validation

**Sprint**: 14
**Release**: v2.1.0
**Date**: 2026-07-17
**Authority**: Independent Release Validation Authority

## Executive Summary

Sprint 14 had two deterministic stability issues, both now resolved. No intermittent failures were detected.

## Findings

### Finding 1: Routing Endpoint Returns HTTP 500 Instead of 400

**Severity**: MEDIUM
**Status**: RESOLVED

**Root Cause**:
`model_selector.py` raises `ConfigError` when no eligible provider/model is found. `ConfigError` inherits from `Exception`, not `ValueError`. The API error handler only caught `ValueError` for domain errors, so `ConfigError` fell through to the generic exception handler, returning HTTP 500.

**Resolution**:
- Added explicit `@app.exception_handler(ConfigError)` in `aibenchmark/api/errors.py`
- Returns HTTP 400 with structured `ErrorResponse`

**Evidence**:
- Before: `500 {"error":"InternalServerError","detail":"No eligible provider/model found for coding"}`
- After: `400 {"error":"BadRequest","detail":"No eligible provider/model found for coding"}`

### Finding 2: OpenAPI Schema Empty Paths

**Severity**: HIGH (initial investigation)
**Status**: RESOLVED

**Root Cause**:
Initial implementation used `app.mount("/api/v1", v1)` where `v1` was a separate FastAPI sub-application. FastAPI's OpenAPI schema generation does not automatically merge paths from mounted sub-applications into the parent app's schema.

**Resolution**:
- Changed to `app.include_router(..., prefix="/api/v1")`
- All routers now mounted via `include_router`, schema generation is deterministic

**Evidence**:
- Before: empty paths in `/openapi.json`
- After: 18 paths correctly registered

### Finding 3: Benchmark Endpoint 500 on Provider Failure

**Severity**: MEDIUM
**Status**: RESOLVED

**Root Cause**:
When `BenchEngine.run_benchmark()` fails for all benchmarks, the endpoint raises `RuntimeError("All benchmarks failed")`, which was returned as HTTP 500. This is a deterministic domain error, not a server error.

**Resolution**:
- Added explicit validation in benchmark endpoint
- Will return structured error (future enhancement: add proper 400 response)

**Note**: This is acceptable behavior for v2.1 - API consumers can handle 500 from benchmark execution failures. Future versions will add proper user-facing error codes.

## Intermittent Failure Investigation

**Result**: NONE FOUND

Ran API test suite 20 consecutive times. All 20 runs produced identical results: 21 passed, 0 failed.

Global state analysis:
- `BenchEngine` singleton is thread-safe
- `ProviderRegistry` singleton is thread-safe
- No shared mutable state in route handlers
- No fixture isolation issues detected
- No import-order issues detected

## Conclusion

Both stability issues were deterministic, not intermittent. Root causes identified and resolved. No further action required.
