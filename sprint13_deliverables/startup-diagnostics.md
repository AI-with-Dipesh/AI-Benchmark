# Startup Diagnostics — Design and Usage

**Sprint**: 13
**Date**: 2026-07-17

## Overview

`BenchEngine.diagnostics_summary()` provides a structured snapshot of system state at startup, including provider discovery, authentication status, and model cache health.

## CLI Usage

```bash
python -m aibenchmark.cli diagnostics
```

## Output Sections

### Benchmarks Loaded

Count of registered benchmark plugins.

### Configured Providers

Provider names parsed from `configs/providers.yaml`.

### Discovered Providers

Provider names actually loaded by the plugin manager. May include providers registered via setuptools entry points but not explicitly configured.

### Authenticated Providers

Providers with non-empty API keys resolved from environment variables.

### Missing API Credentials

Providers whose API keys are missing, along with the expected environment variable name.

### Model Cache

Cached provider count and cache file path.

### Actionable Guidance

Printed when missing API credentials are detected:
> Set the environment variables listed above, then run `benchmark auth` to verify.

## Integration

`BenchEngine.__init__()` now initializes `self._startup_diagnostics = {}`. The diagnostics are collected lazily on first call to `diagnostics_summary()` to avoid startup cost.

## Programmatic Access

```python
from aibenchmark.app.engine import BenchEngine

engine = BenchEngine()
print(engine.diagnostics_summary())
```

## Notes

- Diagnostics do not trigger provider network calls
- Missing API credentials produce warnings but do not block config loading
