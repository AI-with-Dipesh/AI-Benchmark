# Verified Defects

## D-001: PluginManager Type Safety

**Status**: CONFIRMED DEFECT  
**Severity**: Medium  
**Component**: `aibenchmark/app/plugin/manager.py`  
**Methods affected**: `list_names`, `get`, `unload`, `set_enabled`, `get_priority`, `set_priority`, `add_alias`

**Issue**: All methods accept `PluginCategory` enum and unconditionally call `.value`. Passing a string raises `AttributeError`.

**Reproduction**:
```python
from aibenchmark.app.plugin.manager import PluginManager
mgr = PluginManager()
mgr.list_names('provider')  # AttributeError: 'str' object has no attribute 'value'
```

**Fix**: Accept both `PluginCategory` and `str`, coerce to enum before use.
**Impact**: Medium - only affects direct API callers using strings.
**Recommendation**: Patch Release

---

## D-002: Model Registry Returns Empty Without API Keys

**Status**: CONFIRMED DEFECT  
**Severity**: Medium  
**Component**: `aibenchmark/app/provider_registry.py`  
**Method**: `list_models()`

**Issue**: `list_models()` initializes provider with empty credentials. Providers that require API keys return empty model lists.

**Reproduction**:
```python
from aibenchmark.app.provider_registry import ProviderRegistry
reg = ProviderRegistry()
reg.list_models('openrouter')  # Returns []
```

**Fix**: Add local model cache with TTL; fallback to cached models when API unavailable.
**Impact**: Medium - blocks routing in unauthenticated environments.
**Recommendation**: Minor Release

---

## D-003: Strategy Plugins Not Auto-Discovered

**Status**: CONFIRMED DEFECT  
**Severity**: Low  
**Component**: `aibenchmark/plugins/__init__.py`

**Issue**: Strategy plugins (`execution_policy`, `model_selector`) are not imported by `aibenchmark/plugins/__init__.py`, so `discover()` does not register them. They are only registered when imported directly by `engine.py`.

**Reproduction**:
```python
import aibenchmark.plugins
from aibenchmark.app.plugin.registry import get_manager
from aibenchmark.app.models import PluginCategory
get_manager().list_names(PluginCategory.STRATEGY)  # Returns []
```

**Fix**: Add strategy imports to `aibenchmark/plugins/__init__.py`.
**Impact**: Low - strategies load correctly when engine initializes.
**Recommendation**: Future Enhancement

---

## Not Defects

- **N/A**: Decorator registration works correctly
- **N/A**: Entry-point discovery works correctly when entry points exist
- **N/A**: Benchmark calculations are mathematically correct
- **N/A**: Recommendation engine is fully functional
- **N/A**: Decision engine is fully functional
- **N/A**: Historical storage is correct
