# Configuration Findings

## CF-001: Entry Points Not Configured

**Severity**: Low  
**Impact**: External plugins cannot be installed via pip

**Current State**: `pyproject.toml` has entry-point stubs but no actual entry points defined.

**Evidence**:
```toml
[project.entry-points."aibenchmark.providers"]
# Built-in providers are registered via decorator in aibenchmark.plugins
# External plugins can add new providers here

[project.entry-points."aibenchmark.benchmarks"]
# Built-in benchmarks are registered via decorator in aibenchmark.plugins
# External plugins can add new benchmarks here
```

**Fix**: Add entry points for built-in plugins or remove stubs.
**Recommendation**: Future Enhancement

---

## CF-002: Missing Provider API Keys

**Severity**: Medium  
**Impact**: Model discovery and live benchmarking unavailable

**Current State**: `configs/providers.yaml` has provider configurations but no API keys populated.

**Evidence**:
```yaml
openrouter:
  base_url: "https://openrouter.ai/api/v1"
  api_key_env: "OPENROUTER_API_KEY"
  # No api_key set
```

**Fix**: Populate API keys in configuration or environment variables.
**Recommendation**: Deployment prerequisite

---

## CF-003: Strategy Plugins Not Auto-Loaded

**Severity**: Low  
**Impact**: Strategy plugins not visible in `benchmark discover`

**Current State**: `aibenchmark/plugins/__init__.py` imports only providers, benchmarks, and reporters.

**Evidence**:
```python
from aibenchmark.plugins.providers import ...
from aibenchmark.plugins.benchmarks import ...
from aibenchmark.plugins.reporters import ...
# No strategy imports
```

**Fix**: Add strategy imports or document on-demand loading pattern.
**Recommendation**: Future Enhancement
