# Plugin Compatibility

This document defines the Plugin API versioning rules for AI-Benchmark Sprint 8.

## `plugin_api_version`

Every plugin class should declare a `plugin_api_version` string:

```python
class MyProvider:
    plugin_api_version = "1.0"
```

- `"1.0"` is the current stable version (Sprint 8).
- Missing `plugin_api_version` is treated as compatible but generates a warning.
- Versions are compared as major numbers only; minor versions are ignored for compatibility.

## Registration and Validation

The plugin manager validates the following during registration:

1. `plugin_api_version` is present and a string.
2. If the version is not `"1.0"`, a `CompatibilityWarning` is emitted.
3. Unknown top-level attributes on plugin classes are warned but do not fail registration.

## CLI Commands

```bash
benchmark plugin validate          Validate metadata and API version for all plugins
benchmark provider validate-compat Show detailed compatibility report per provider
```

## Migration

When the API changes:

- Increment the major version: `1.0` -> `2.0`.
- Update this document with a migration guide.
- Provide a backwards-compatibility shim in `aibenchmark/plugin/` for at least one sprint.
