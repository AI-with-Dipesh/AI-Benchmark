# Developer Guide — AI-Benchmark

This guide covers local development setup, testing, plugin development, CI workflow, governance workflow, and contribution guidelines for the AI-Benchmark project.

## Table of Contents

1. [Development Setup](#development-setup)
2. [Environment Preparation](#environment-preparation)
3. [Running Tests](#running-tests)
4. [Coverage Workflow](#coverage-workflow)
5. [Plugin Development](#plugin-development)
6. [CI Workflow](#ci-workflow)
7. [Governance Workflow](#governance-workflow)
8. [Contribution Guidelines](#contribution-guidelines)
9. [Useful Commands](#useful-commands)

## Development Setup

### Prerequisites

- Python 3.13+
- Git
- Virtual environment tool (venv or virtualenv)

### Clone Repository

```bash
git clone git@github.com:AI-with-Dipesh/AI-Benchmark.git
cd AI-Benchmark
```

### Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# or
.venv\Scripts\activate  # Windows
```

### Install Dependencies

```bash
pip install -e ".[dev]"
```

### Verify Installation

```bash
python -m aibenchmark.cli --help
```

## Environment Preparation

### Python Version

Project targets Python 3.13. Ensure your runtime matches:

```bash
python --version  # Should show 3.13.x
```

### Provider API Keys

Some tests and benchmarks require provider API keys. Set them as environment variables:

```bash
export NVIDIA_API_KEY="your-key"
export OPENROUTER_API_KEY="your-key"
export OLLAMA_API_KEY="your-key"  # optional for local Ollama
export HF_API_KEY="your-key"
```

### Configuration Files

The project uses YAML configuration files in `configs/`:

- `configs/benchmark.yaml` — benchmark weights and routing strategy
- `configs/providers.yaml` — provider endpoints and API key environment variables

Copy `examples/benchmark.example.yaml` to `configs/benchmark.yaml` if starting from scratch.

### Lint/Type Checker Setup

```bash
pip install ruff mypy
```

Verify tools:

```bash
ruff --version
mypy --version
```

## Running Tests

### Full Test Suite

```bash
pytest aibenchmark/tests/ -q
```

Expected output: `386 passed, 6 skipped` (or higher as coverage expands).

### Single Test File

```bash
pytest aibenchmark/tests/test_config.py -v
```

### Single Test Function

```bash
pytest aibenchmark/tests/test_config.py::test_config_loads_providers_and_weights -v
```

### Test with Warnings as Errors

```bash
pytest aibenchmark/tests/ -W error::ResourceWarning -q
```

## Coverage Workflow

### Run Coverage

```bash
pytest aibenchmark/tests/ --cov=aibenchmark --cov-report=term -q
```

### Coverage with Missing Lines

```bash
pytest aibenchmark/tests/ --cov=aibenchmark --cov-report=term-missing -q
```

### HTML Coverage Report

```bash
pytest aibenchmark/tests/ --cov=aibenchmark --cov-report=html
open htmlcov/index.html  # or xdg-open on Linux
```

### Coverage Goals

- Current target: ≥94%
- Long-term target: 95%
- All new tests should maintain or improve coverage.

## Plugin Development

### Plugin Categories

AI-Benchmark supports five plugin categories:

- **Providers** (`aibenchmark/plugins/providers/`) — LLM provider integrations
- **Benchmarks** (`aibenchmark/plugins/benchmarks/`) — evaluation benchmarks
- **Reporters** (`aibenchmark/plugins/reporters/`) — output formatters
- **Evaluators** (`aibenchmark/plugins/evaluators/`) — scoring engines
- **Strategies** (`aibenchmark/plugins/strategies/`) — routing and execution policies

### Development Mode

When running from a source checkout (editable install via `pip install -e .`), plugins are discovered through **decorator registration** rather than `setuptools` entry points. The `PluginManager` automatically initializes the built-in plugin set by importing `aibenchmark.plugins`, which triggers the `@register` decorator side-effects.

This means:
- No `pyproject.toml` entry-point configuration is required for built-in plugins.
- New plugins added to `aibenchmark/plugins/` are loaded immediately on the next process start.
- External plugin discovery via entry points is available when the package is installed with entry points defined.

### Creating a Plugin

1. Choose the appropriate category directory.
2. Create a new Python file (e.g., `my_benchmark.py`).
3. Import the base interface and `register` decorator.
4. Implement required methods.
5. Set `plugin_api_version = "1.0"`.

#### Example: Simple Benchmark Plugin

```python
from __future__ import annotations

from aibenchmark.interfaces.benchmark import BaseBenchmark
from aibenchmark.app.models import BenchmarkName, BenchmarkResult, PluginCategory, ResponseObject, Score
from aibenchmark.app.plugin.registry import register

@register(PluginCategory.BENCHMARK, "my_benchmark")
class MyBenchmark(BaseBenchmark):
    name = BenchmarkName.MY_BENCHMARK  # Add to BenchmarkName enum if needed
    plugin_name = "my_benchmark"
    plugin_api_version = "1.0"

    def run(self, response: ResponseObject, **kwargs) -> BenchmarkResult:
        # Implement benchmark logic
        score = Score(
            benchmark=self.name,
            raw=0.0,
            normalized=0.0,
            weight=1.0,
            weighted=0.0,
        )
        return BenchmarkResult(
            model="",
            provider="",
            scores=[score],
            overall=0.0,
        )
```

### Registering Plugins

**Built-in / development mode**: Use the `@register` decorator. The plugin is registered at import time when `aibenchmark.plugins` is imported.

**External plugins**: Register via setuptools entry points in `pyproject.toml`:

```toml
[project.entry-points."aibenchmark.benchmarks"]
my_benchmark = "my_package.plugins:MyBenchmark"
```

> Note: Entry-point discovery is the preferred mechanism for external plugins distributed via PyPI. Decorator registration remains the primary mechanism for built-in plugins during development.

### Plugin API Version

All plugins must declare `plugin_api_version = "1.0"`. Plugins with mismatched versions may be rejected by the plugin manager with a `PluginCompatibilityWarning`.

### Plugin Load Order

1. `PluginManager.__init__()` creates empty stores.
2. `BenchEngine.__init__()` imports `aibenchmark.plugins`, triggering decorator side-effects.
3. For entry-point discovery, call `PluginManager.discover()` explicitly.

### PluginManager API Boundaries

The `PluginManager` accepts both `PluginCategory` enum values and plain strings at public API boundaries:

```python
mgr.list_names("benchmark")          # string accepted
mgr.list_names(PluginCategory.BENCHMARK)  # enum accepted
mgr.get("provider", "openrouter")     # string accepted
mgr.register("benchmark", "x", cls)   # string accepted
```

Internal code should continue using strongly typed enums.

### Provider Configuration

Provider settings live in `configs/providers.yaml`. Each provider entry supports:

- `api_key_env` — environment variable name for the API key
- `base_url` — optional custom endpoint
- Other provider-specific settings

API keys are resolved at config load time from the environment. Providers with missing API keys will log a warning and raise `ValueError` on initialization.

### Local Model Cache

The `ProviderRegistry` includes an optional file-backed model cache to improve offline and startup performance:

- **Location**: `~/.aibenchmark/model_cache.json`
- **TTL**: 1 hour (configurable via `ProviderRegistry(cache_ttl=...)`)
- **Behavior**: 
  - Live model lists are cached on successful fetch.
  - If a provider is temporarily unavailable, the cache is used as a fallback.
  - Stale cache entries are never returned when live data succeeds.

View cache statistics:

```bash
python -m aibenchmark.cli diagnostics
```

Invalidate the cache manually:

```python
from aibenchmark.app.provider_registry import ProviderRegistry
registry = ProviderRegistry()
registry.model_cache.invalidate("openrouter")
registry.model_cache.invalidate()  # clear all
```

## CI Workflow

### Workflows

- **test.yml** — runs pytest, ruff, mypy, docs validation, and governance validation on every push and PR.
- **security-scan.yml** — runs Bandit and Safety dependency audit after tests pass.
- **release.yml** — creates GitHub releases from tags.

### CI Quality Gates

| Job | Command | Pass Criterion |
|-----|---------|----------------|
| test | `pytest aibenchmark/tests/ -q` | 0 failures |
| lint | `ruff check aibenchmark/` | 0 errors |
| type-check | `mypy -p aibenchmark` | ≤40 errors (accepted debt) |
| docs-accuracy | custom script | exits 0 |
| governance-validate | `python scripts/validate_governance_docs.py` | exits 0 |

### Running CI Locally

```bash
# Run tests
pytest aibenchmark/tests/ -q

# Lint
ruff check aibenchmark/

# Type check
mypy -p aibenchmark

# Governance validation
python scripts/validate_governance_docs.py
```

## Governance Workflow

### Sprint Structure

Each sprint follows the formal governance lifecycle:

1. Sprint Planning
2. Implementation
3. Internal QA
4. QA Resolution
5. QA Re-Validation
6. RC Validation
7. RC Validation Resolution
8. RC Re-Validation
9. Acceptance Review
10. Formal Acceptance
11. Repository Audit
12. Repository Audit Resolution
13. Repository Re-Audit
14. Release Snapshot
15. Release Publication
16. Release Confirmation
17. Repository Synchronization Re-Validation
18. Engineering Baseline Certification

### Governance Documents

All sprint governance documents live in `docs/reviews/` and follow the naming convention:

- `sprint-{N}-{stage}.md`
- `v{version}-release-{artifact}.md`

Documents must be committed before advancing to the next stage.

### Governance Validation

The governance validation tool enforces document persistence:

```bash
python scripts/validate_governance_docs.py
```

This runs in CI on every push and ensures no governance documents are accidentally deleted.

### Technical Debt Register

Technical debt is tracked in `docs/reviews/sprint-{N}-technical-debt.md` with:

- ID, description, priority, origin sprint, recommended sprint, risk, owner, status
- Remediation plan with milestones
- Evidence of workaround or mitigation

## Contribution Guidelines

### Branching Model

- `master` — protected branch, contains production-ready code
- Feature work should be done in feature branches and merged via PR.

### Commit Messages

Follow conventional commits style:

```
type(scope): description
```

Types:
- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation only
- `chore`: maintenance, dependency updates
- `test`: test additions or fixes
- `refactor`: code refactoring (no behavior change)
- `type`: type annotation changes only

### Pull Request Checklist

- [ ] All tests pass: `pytest aibenchmark/tests/ -q`
- [ ] Ruff passes: `ruff check aibenchmark/`
- [ ] MyPy passes: `mypy -p aibenchmark`
- [ ] Coverage maintained or improved
- [ ] Documentation updated if behavior changed
- [ ] Governance documents updated if sprint stage advanced
- [ ] No unintended architecture changes

### Code of Conduct

- Be respectful and inclusive.
- Focus on constructive feedback.
- Prioritize project goals over personal preferences.

## Useful Commands

```bash
# Activate virtual environment
source .venv/bin/activate

# Run full quality gate locally
pytest aibenchmark/tests/ --cov=aibenchmark -q && ruff check aibenchmark/ && mypy -p aibenchmark && python scripts/validate_governance_docs.py

# Run specific test by keyword
pytest aibenchmark/tests/ -k "test_config" -v

# Show ruff errors with suggestions
ruff check aibenchmark/ --show-settings

# MyPy with specific error codes disabled
mypy -p aibenchmark --disable-error-code=unused-ignore

# List all registered plugins
python -m aibenchmark.cli discover

# Generate a benchmark report
python -m aibenchmark.cli run main -m gpt-4o-mini -b latency -o reports/
```

## License

AI-Benchmark is released under the MIT License. See LICENSE file for details.
