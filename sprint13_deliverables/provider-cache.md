# Provider Model Cache — Design and Usage

**Sprint**: 13
**Date**: 2026-07-17

## Overview

The `ModelCache` provides a file-backed, TTL-expiring cache for provider model lists. It allows the benchmark engine to function partially when providers are unavailable.

## Location

Default file: `~/.aibenchmark/model_cache.json`

## Behavior

### Normal Operation (Live Success)

1. `ProviderRegistry.list_models(provider)` is called
2. Provider returns live model list
3. Cache is updated with live data
4. Live data is returned to caller

### Fallback Operation (Live Failure)

1. `ProviderRegistry.list_models(provider)` is called
2. Provider raises an exception or returns empty list
3. Cache is checked for existing entry
4. If cached entry exists (even if expired), cache is returned
5. If no cached entry, empty list is returned

### Key Constraint

Stale cache is **never** returned when live data is available. The cache is updated on every successful live fetch.

## API

### ModelCache

```python
from aibenchmark.app.provider_cache import ModelCache

cache = ModelCache(path=Path("custom.json"), ttl=600)

models = cache.get("openrouter")       # returns list[str] | None
cache.set("openrouter", ["gpt-4o", "o1"])  # update cache
cache.invalidate("openrouter")         # clear single provider
cache.invalidate()                     # clear all
stats = cache.stats()                  # {"cached_providers": 1, ...}
```

### ProviderRegistry Integration

```python
from aibenchmark.app.provider_registry import ProviderRegistry

registry = ProviderRegistry(cache_ttl=1800)  # 30 minutes
models = registry.list_models("openrouter")
```

## CLI

View cache statistics:

```bash
python -m aibenchmark.cli diagnostics
```

## Testing

- `test_sprint13_maintenance.py::TestModelCache` — cache behavior
- `test_sprint13_maintenance.py::TestProviderRegistryCache` — integration tests

## Notes

- Atomic writes: data is written to `.tmp` file, then renamed
- Cache writes are fire-and-forget; failures are logged at debug level
- Cache misses and expiration are silent (no user-facing noise)
