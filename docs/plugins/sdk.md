# Plugin SDK

This is the stub documentation for the AI-Benchmark Plugin SDK. The full Plugin SDK is delivered in Sprint 8.

## Overview

AI-Benchmark uses an entry-point based plugin system. Plugins are registered via `pyproject.toml` entry points or via decorator registration.

## Plugin Categories

| Category | Enum Value |
|----------|-----------|
| Provider | `provider` |
| Benchmark | `benchmark` |
| Evaluator | `evaluator` |
| Reporter | `reporter` |
| Strategy | `strategy` |

## Plugin API Version

Plugins declare their compatibility with:

```python
plugin_api_version = "1.0"
```

Compatibility rules and migration guidance are documented in [plugins/compatibility.md](./compatibility.md).

## Registration

Use the `@register` decorator from `aibenchmark.app.plugin.registry`:

```python
from aibenchmark.app.plugin.registry import register
from aibenchmark.app.models import PluginCategory

@register(PluginCategory.PROVIDER)
class MyProvider:
    plugin_api_version = "1.0"
    plugin_name = "my_provider"
    plugin_enabled = True
    plugin_priority = 100
    plugin_aliases = []
    
    def list_models(self):
        ...
    
    def run(self, model, messages):
        ...
```

## Validate Plugins

```bash
benchmark plugin validate
benchmark provider validate-compat
```

## See Also

- [Plugin Compatibility Guide](./compatibility.md)
- [Writing Benchmarks](../usage/writing-benchmarks.md)
