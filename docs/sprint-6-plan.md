# Sprint 6 Planning Document

**Project:** AI-Benchmark
**Baseline:** v0.5.0 (Sprint 5: Universal Provider Platform)
**Target:** v0.6.0
**Date:** 2026-07-13
**Status:** Planning — Architecture Resolution Complete

---

## 1. Executive Summary

Sprint 6 transforms AI-Benchmark from a **single-provider benchmarking tool** into an **intelligent multi-provider orchestration platform**. While Sprint 5 established the provider abstraction layer, Sprint 6 adds the decision engine that automatically selects providers, models, and fallback strategies based on benchmark requirements, provider health, cost constraints, and historical performance.

### Sprint 6 Theme
**"Intelligent Routing & Automatic Model Selection"**

### Primary Objectives
- Introduce LiteLLM-style routing configuration generation
- Implement automatic model selection based on category requirements
- Add fallback strategies with explicit separation from retry logic
- Build cost-optimized execution paths through model selection
- Enable multi-provider parallel execution with thread-safety infrastructure
- Generate provider-specific execution reports

### Scope Constraints
- Do NOT redesign the benchmark engine
- Do NOT modify the provider interface contract
- Do NOT break backward compatibility
- Do NOT introduce LiteLLM runtime dependencies
- Do NOT implement agent orchestration
- Only add new modules, CLI commands, and reporter plugins
- All new behavior is opt-in via configuration

---

## 2. Current Architecture Review

### Core Components

| Component | Location | Responsibility |
|-----------|----------|----------------|
| BenchEngine | `app/engine.py` | Coordinates benchmark runs, retries, metadata |
| PluginManager | `app/plugin/manager.py` | Plugin lifecycle |
| ProviderRegistry | `app/provider_registry.py` | Provider discovery, lookup, validation |
| ProviderHealth | `app/provider_health.py` | Health tracking and status |
| ProviderCapabilities | `app/provider_capabilities.py` | Capability flag detection |
| AuthLayer | `app/auth.py` | Authentication |
| RateLimits | `app/rate_limits.py` | Rate limit handling |
| Certification | `app/certification.py` | Provider scoring |
| CrossProvider | `app/cross_provider.py` | Cross-provider comparison |
| AppConfig | `app/config.py` | YAML configuration |
| CostEstimator | `app/engine.py` | Post-run cost estimation |
| History | `app/history.py` | SQLite persistence |

### Plugin System
- **Providers:** 4 registered (nvidia, openrouter, ollama, huggingface)
- **Benchmarks:** 9 categories (coding, debugging, reasoning, research, general, code_review, instruction, json, latency)
- **Reporters:** 6 (json, markdown, csv, sprint4, provider_comparison, provider_health, capabilities)
- **Evaluators:** Pluggable external evaluators
- **Strategies:** Pluggable execution strategies

### Provider Platform
- 22-method universal interface
- 13 capability flags per provider
- 10 health metrics per provider
- 4 certification levels
- 16-field metadata per provider
- Environment variable, .env, and config file authentication

### Configuration
- `configs/providers.yaml` — provider endpoints and auth
- `configs/benchmark.yaml` — weights, retry, timeout, cost, run defaults
- Externalized: no hardcoded values
- Python 3.13+, type-annotated

### Test Coverage
- 201 passing tests
- 6 skipped integration tests
- 90% coverage
- Sprint 5: 12 new test files

### Known Technical Debt
1. Pre-existing mypy/ruff issues in Sprint 1-3 modules
2. `enabled`/`priority`/`aliases` config keys parsed but not enforced at plugin load time
3. Top-level `benchmark capabilities` CLI duplication with `benchmark provider capabilities`
4. `benchmark_version` in config defaults to "0.4.0" instead of current version
5. No CI/CD pipeline
6. `HealthTracker` and `HistoryWriter` lack thread-safety infrastructure

---

## 3. Technical Debt Assessment

| ID | Item | Priority | Impact | Risk | Recommended Sprint | Action |
|----|------|----------|--------|------|-------------------|--------|
| TD-1 | Pre-existing mypy/ruff issues in Sprint 1-3 | Low | Low | Low | Sprint 7+ | Defer |
| TD-2 | `enabled`/`priority`/`aliases` not enforced at load | Low | Low | Low | Sprint 7 | Defer |
| TD-3 | CLI duplication: `benchmark capabilities` vs `benchmark provider capabilities` | Low | Low | Low | Sprint 7 | Defer |
| TD-4 | `benchmark_version` defaults to 0.4.0 | Medium | Medium | Medium | Sprint 6 | **Fix in Sprint 6** |
| TD-5 | No CI/CD pipeline | Medium | High | Medium | Sprint 6 | **Add in Sprint 6** |
| TD-6 | No GitHub Actions workflows | Medium | Medium | Low | Sprint 6 | **Add in Sprint 6** |
| TD-7 | Pre-existing type issues in `analytics.py`, `history.py` | Low | Low | Low | Sprint 7+ | Defer |
| TD-8 | No examples directory | Low | Low | Low | Sprint 7+ | Defer |
| TD-9 | `HealthTracker` not thread-safe | **High** | **High** | **High** | **Sprint 6** | **Fix in Sprint 6** |
| TD-10 | `HistoryWriter` lacks write serialization | **High** | **High** | **High** | **Sprint 6** | **Fix in Sprint 6** |

### Sprint 6 Technical Debt Resolution
| Item | Action |
|------|--------|
| TD-4 | Update `AppConfig.benchmark_version` default to "0.5.0" and read from `pyproject.toml` |
| TD-5 | Add GitHub Actions CI workflow (test, lint, type-check) |
| TD-6 | Add release automation workflow |
| TD-9 | Add `threading.Lock` to `HealthTracker` and any shared mutable state accessed by parallel executor |
| TD-10 | Add `HistoryWriter` singleton with write serialization for SQLite |

---

## 4. Sprint 6 Objectives

### Primary Goal
Add intelligent routing, automatic model selection, and fallback strategies without modifying the benchmark engine or provider interface.

### Success Criteria
1. LiteLLM-style routing config can be generated from provider capabilities and health
2. Automatic model selection works for all 9 benchmark categories
3. Fallback chains execute after retry exhaustion, with clear retry/fallback separation
4. Cost-aware selection reduces benchmark execution cost by ≥15% in test scenarios
5. Multi-provider parallel execution works for non-stateful benchmarks with thread-safe shared state
6. All new functionality is covered by unit tests (≥90% coverage on new code)
7. Backward compatibility: all existing CLI commands continue to work unchanged

---

## 5. Proposed Features

### 5.1 LiteLLM Configuration Generation
- **Module:** `plugins/reporters/litellm_config.py`
- Generate LiteLLM-compatible YAML configuration from:
  - Provider capabilities
  - Provider health status
  - Provider metadata
  - Cost configuration
  - Authentication configuration
- Output: `configs/litellm.yaml` (auto-generated, gitignored)
- No LiteLLM runtime dependency — configuration output only
- Registered as reporter plugin

### 5.2 Intelligent Model Selection
- **Module:** `app/model_selector.py`
- Registered as `PluginCategory.STRATEGY` plugin
- Automatic model selection based on:
  - Benchmark category requirements (coding needs function_calling, reasoning needs long_context)
  - Provider capabilities match
  - Provider health (exclude unhealthy providers)
  - Cost constraints (prefer cheaper models when quality threshold met)
  - Historical performance (from SQLite history)
  - Context window feasibility check
- Deterministic output with explicit tie-breaking rules
- Default fallback to configured model if no qualified candidate exists

### 5.3 Fallback Strategies (ExecutionPolicy)
- **Module:** `app/execution_policy.py`
- Replaces `app/fallback.py`
- Clear separation from retry:
  - **Retry:** same provider/model, transient failures, bounded attempts with exponential backoff (engine-owned)
  - **Fallback:** alternate provider/model, structural failures, circuit-breaker aware (policy-owned)
- Strategies:
  - **Provider alternation:** try secondary provider on fallback
  - **Model alternation:** try alternative model on same provider on fallback
  - **Category skip:** produce explicit `BenchmarkResult(status="skipped")` instead of omitting
- Circuit breaker: exclude providers with `failure_rate > 0.5` for configurable cooldown
- Configurable per benchmark in `configs/benchmark.yaml`

### 5.4 Cost-Aware Model Selection
- **Module:** Merged into `app/model_selector.py`
- Cost is a selection input, not a separate routing layer
- Route benchmarks to cheapest qualified provider/model via selection strategy
- Threshold-based: if cost delta < X%, prefer higher capability
- Budget enforcement: raise `ConfigError` if estimated cost exceeds ceiling before execution
- Reuses `AppConfig.model_cost()` — no duplicate estimation

### 5.5 Multi-Provider Parallel Execution
- **Module:** `app/parallel_executor.py`
- Execute independent benchmarks across multiple providers simultaneously
- Thread-pool based with configurable concurrency
- Opt-in via `parallel.enabled` in config
- Result aggregation with deterministic ordering
- Rate-limit awareness using `ProviderHealth` status
- Thread-safe boundaries:
  - `HealthTracker` mutations protected by `threading.Lock`
  - SQLite writes serialized via `HistoryWriter` singleton
  - Provider instances not shared across threads
- **Performance target: ≥1.5x speedup** with linear scaling trend
- Benchmarks verified as idempotent before parallel execution allowed

### 5.6 Provider-Specific Prompt Optimization
- **Status:** DEFERRED TO SPRINT 7
- Rationale: Doubles prompt matrix (9 × 4 = 36), low proportional value vs. scope
- Future implementation path: provider plugin method `optimize_prompt(prompt, model)`

### 5.7 CLI Additions
| Command | Description |
|---------|-------------|
| `benchmark route` | Show routing plan for benchmark without executing |
| `benchmark select` | Automatic model selection for category |
| `benchmark fallback` | Test fallback chain for provider/model |
| `benchmark optimize` | Cost-optimized benchmark execution |
| `benchmark parallel` | Multi-provider parallel execution |
| `benchmark config generate-litellm` | Generate LiteLLM config |

### 5.8 Report Additions
| Report | Description |
|--------|-------------|
| `routing` | Routing plan and rationale |
| `optimization` | Cost optimization analysis |
| `fallback` | Fallback chain test results |
| `comparison_detailed` | Enhanced cross-provider comparison with cost/latency scatter |

---

## 6. Architecture Impact

### New Modules (6)

| Module | Location | Responsibility | Notes |
|--------|----------|----------------|-------|
| `app/model_selector.py` | Core | Automatic model selection engine | Registered as strategy plugin |
| `app/execution_policy.py` | Core | Fallback/circuit-breaker policy | Replaces `fallback.py` |
| `plugins/reporters/litellm_config.py` | Reporter | LiteLLM YAML generation | Moved from `app/litellm_config.py` |
| `plugins/reporters/routing.py` | Reporter | Routing plan report | |
| `plugins/reporters/optimization.py` | Reporter | Cost optimization report | |
| `app/parallel_executor.py` | Core | Parallel execution coordinator | Thread-safe; opt-in |

### Modified Modules (5)

| Module | Changes | Risk |
|--------|---------|------|
| `app/engine.py` | Add strategy-plugin delegation point for selection/policy | Medium |
| `app/config.py` | Parse `routing` section with validation schema | Medium |
| `app/models.py` | Add `RoutingPlan`, `ExecutionPolicy`, `RoutingContext` dataclasses | Low |
| `app/provider_health.py` | Add `threading.Lock` to `HealthTracker` | Medium |
| `app/history.py` | Add `HistoryWriter` singleton with write serialization | Medium |

### New Plugin Types (0)
All new functionality uses existing plugin types (strategy, reporter) or internal modules. No new plugin categories.

### Backward Compatibility
- All existing CLI commands unchanged
- All existing provider plugins unchanged
- All existing benchmark plugins unchanged
- All existing reporter plugins unchanged
- New config keys optional with sensible defaults
- Parallel execution disabled by default

---

## 7. Interface Design

### Strategy Plugin Interface (PluginCategory.STRATEGY)

```python
# app/interfaces/strategy.py
from abc import ABC, abstractmethod
from typing import Any

class BaseStrategy(ABC):
    plugin_name: str = ""
    plugin_category: str = "strategy"

    @abstractmethod
    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        ...
```

### RoutingContext Dataclass

```python
# app/models.py addition
@dataclass(frozen=True)
class RoutingContext:
    benchmark_name: BenchmarkName
    provider_name: str | None = None
    model: str | None = None
    max_cost: float | None = None
    required_capabilities: list[str] = field(default_factory=list)
    prefer_free: bool = False
    min_capability_score: float = 0.7
    history_runs: int = 5
```

### RoutingPlan Dataclass

```python
# app/models.py addition
@dataclass(frozen=True)
class RoutingPlan:
    provider: str
    model: str
    estimated_cost: float | None = None
    rationale: str = ""
    fallback_providers: list[str] = field(default_factory=list)
    fallback_models: list[str] = field(default_factory=list)
```

### ExecutionPolicy Dataclass

```python
# app/models.py addition
@dataclass(frozen=True)
class ExecutionPolicy:
    retry_count: int = 2
    backoff_factor: float = 1.5
    fallback_enabled: bool = False
    fallback_chain: list[str] = field(default_factory=list)
    circuit_breaker_threshold: float = 0.5
    circuit_breaker_cooldown_seconds: int = 300
```

---

## 8. Concurrency Architecture

### Shared State Analysis

| Component | Current State | Concurrency Risk | Mitigation |
|-----------|--------------|------------------|------------|
| HealthTracker | Mutable dict/deque, global singleton | 🔴 High | Add `threading.Lock` around `_samples` and `_states` mutations |
| History Writer | SQLite connection per call | 🔴 High | Add `HistoryWriter` singleton with single connection and lock |
| PluginManager | Class-level mutable attrs | 🟡 Medium | No mutation during parallel execution; safe if frozen at start |
| AppConfig | Mutable dict | 🟢 Low | Immutable after load; no concurrent mutation |
| Provider instances | Created per benchmark | 🟢 Low | Never shared across threads |

### Lock Boundaries

```python
# HealthTracker
class HealthTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._samples: dict[str, deque] = {}
        self._states: dict[str, ProviderHealth] = {}

    def record(self, ...):
        with self._lock:
            # mutate _samples and _states

# HistoryWriter
class HistoryWriter:
    _instance = None
    _init_lock = threading.Lock()

    def __init__(self):
        self._conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()

    def save_run(self, ...):
        with self._lock:
            # serialize all DB writes
```

### Failure Isolation

- Each parallel job gets a fresh provider instance.
- Jobs cannot mutate shared state except through locked channels.
- SQLite writes are serialized; reads are lock-free after write completes.
- Engine catches job-level exceptions; partial results are valid.

### Lifecycle

1. Engine loads config (single-threaded).
2. Engine instantiates strategy plugins (single-threaded).
3. Parallel executor spawns workers (multi-threaded).
4. Workers acquire provider instances, execute benchmarks.
5. Workers record health through locked `HealthTracker`.
6. Workers submit results to `HistoryWriter` (serialized).
7. Executor aggregates results deterministically.

---

## 9. Retry vs Fallback Semantics

### Retry (Engine-Owned)

- **Scope:** Same provider, same model, same request
- **Trigger:** Transient failures: timeout, connection error, 429, 5xx
- **Bound:** `retry_count` from config (default 2)
- **Backoff:** Exponential, `backoff_factor` from config
- **Ownership:** `BenchEngine.run_benchmark()` — unchanged from Sprint 5
- **Visibility:** Recorded in `BenchmarkResult.retry_count`

### Fallback (Policy-Owned)

- **Scope:** Alternate provider or alternate model
- **Trigger:** Structural failures: 401, 404, capability mismatch, provider unavailable
- **Bound:** `fallback_chain.length` from config
- **Behavior:**
  - Provider alternation: try next provider in chain
  - Model alternation: try alternative model on same provider
  - Category skip: produce explicit `BenchmarkResult(status="skipped")`
- **Ownership:** `ExecutionPolicy` strategy plugin
- **Visibility:** Recorded in `BenchmarkResult.fallback_chain` and `details`

### Circuit Breaker (Policy-Owned)

- **Scope:** Provider-level exclusion
- **Trigger:** `failure_rate > circuit_breaker_threshold`
- **Cooldown:** `circuit_breaker_cooldown_seconds`
- **Behavior:** Exclude provider from selection during cooldown
- **Ownership:** `ExecutionPolicy` strategy plugin
- **Visibility:** `ProviderHealth.status` reflects circuit state

### Explicit Boundaries

| Concern | Owner | Trigger | Action |
|---------|-------|---------|--------|
| Connection timeout | Engine | TimeoutError | Retry same endpoint |
| HTTP 429 | Engine | RateLimits detected | Retry with backoff |
| HTTP 5xx | Engine | ServerError | Retry same endpoint |
| HTTP 401/404 | Policy | Auth/Not Found | Fallback to alternate provider |
| Capability mismatch | Policy | Provider missing required capability | Fallback or skip |
| High failure rate | Policy | `failure_rate > threshold` | Circuit break |
| Cost ceiling exceeded | Selector | `estimated_cost > max_cost` | Raise ConfigError before execution |
| Parallel error | Executor | Job exception | Record partial result; continue other jobs |

---

## 10. Updated Module Architecture

### Removed Modules
- `app/litellm_config.py` → moved to `plugins/reporters/litellm_config.py`
- `app/cost_router.py` → merged into `app/model_selector.py`
- `app/fallback.py` → replaced by `app/execution_policy.py`
- `app/prompt_optimizer.py` → deferred to Sprint 7

### Final Module List

```
app/
├── model_selector.py          # Strategy plugin: model selection
├── execution_policy.py        # Strategy plugin: fallback + circuit breaker
├── parallel_executor.py       # Thread-safe parallel execution
├── litellm_config.py          # REMOVED (moved to reporter)
├── cost_router.py             # REMOVED (merged into model_selector)
├── fallback.py                # REMOVED (replaced by execution_policy)
plugins/reporters/
├── routing.py                 # Routing plan report
├── optimization.py            # Cost optimization report
├── capabilities.py            # Existing Sprint 5
├── provider_comparison.py     # Existing Sprint 5
├── provider_health.py         # Existing Sprint 5
├── litellm_config.py          # LiteLLM YAML reporter
```

---

## 11. Updated Dependency Diagram

```
BenchEngine
├── PluginManager
├── AppConfig
├── ProviderRegistry
├── HealthTracker (with Lock)
├── HistoryWriter (with Lock)
├── BaseStrategy.select()       [model_selector]
└── BaseStrategy.execute()      [execution_policy]

ParallelExecutor
├── BenchEngine (per provider)
├── HealthTracker (Lock-protected)
└── HistoryWriter (Lock-protected)

ModelSelector (strategy plugin)
├── ProviderRegistry
├── ProviderHealth
├── AppConfig
└── History (optional, for performance queries)

ExecutionPolicy (strategy plugin)
├── ProviderRegistry
├── ProviderHealth
└── AppConfig

RoutingReporter (reporter plugin)
├── BenchmarkResult
├── ProviderRegistry
└── ProviderHealth

OptimizationReporter (reporter plugin)
├── BenchmarkResult
└── AppConfig

LiteLLMConfigReporter (reporter plugin)
├── ProviderRegistry
├── ProviderHealth
└── AppConfig
```

### Dependency Direction Rules
- `app/` modules may depend on `app/models.py`, other `app/` modules, and `interfaces/`.
- `plugins/reporters/` may depend on `app/` and `app/models.py` only.
- No circular dependencies.
- Strategy plugins depend on registries/config, never on engine.

---

## 12. Implementation Roadmap

### Phase 1: Concurrency Infrastructure (Day 0 — Pre-Implementation)
**Goal:** Make shared state thread-safe before parallel code touches it
- Add `threading.Lock` to `HealthTracker`
- Add `HistoryWriter` singleton to `app/history.py`
- Add thread-safety unit tests
- Verify existing tests still pass

**Exit Criteria:**
- HealthTracker passes concurrent write stress test
- HistoryWriter passes concurrent write stress test
- No regressions in 201 existing tests

### Phase 2: Strategy Interfaces & Models (Day 1)
**Goal:** Define contracts for selection, policy, routing
- Add `RoutingContext`, `RoutingPlan`, `ExecutionPolicy` to `models.py`
- Define `BaseStrategy` in `interfaces/strategy.py`
- Implement `ModelSelectorStrategy` (stub)
- Implement `ExecutionPolicyStrategy` (stub)
- Tests: model validation, strategy interface compliance

**Exit Criteria:**
- All new dataclasses pass type checking
- Strategy interface verified by mock implementations

### Phase 3: Core Selection & Policy (Day 2)
**Goal:** Build selection and fallback engines
- Implement `ModelSelectorStrategy` with 4 strategies: cost_aware, capability_first, health_first, round_robin
- Implement `ExecutionPolicyStrategy` with fallback + circuit breaker
- Wire engine to delegate selection/policy via strategy lookup
- Tests: selector strategies, fallback execution, circuit breaker, cost routing

**Exit Criteria:**
- All strategies produce deterministic output
- Fallback executes correctly for simulated failures
- Cost routing respects ceiling
- Engine delegates to strategies without inline logic

### Phase 4: Parallel Execution (Day 3)
**Goal:** Multi-provider parallel benchmark execution
- Implement `ParallelExecutor` with thread pool
- Integrate with `BenchEngine.run_benchmark` via delegation
- Rate-limit-aware scheduling using `ProviderHealth`
- Benchmark idempotency verification
- Tests: parallel correctness, rate limit handling, thread safety

**Exit Criteria:**
- Parallel runs produce same results as sequential
- No race conditions in 4-thread stress test
- No SQLite corruption
- Speedup ≥1.5x on 4-provider scenario

### Phase 5: LiteLLM Config & Reports (Day 4)
**Goal:** Generate LiteLLM config and new reports
- Implement `LiteLLMConfigReporter` as reporter plugin
- Implement `RoutingReporter`
- Implement `OptimizationReporter`
- Add CLI commands
- Integration tests for new CLI commands

**Exit Criteria:**
- Generated LiteLLM config valid YAML
- All CLI commands functional
- All reports generated correctly

### Phase 6: Integration & QA (Day 5)
**Goal:** End-to-end verification
- Add routing config validation to `AppConfig`
- Run full test suite
- Run integration tests with live providers (if available)
- Coverage report
- Performance benchmark

**Exit Criteria:**
- 201 existing tests + new tests all pass
- 90%+ overall coverage
- No regressions in Sprint 1-5 functionality
- Routing config validation catches invalid keys

### Phase 7: Documentation & Release Prep (Day 5+)
**Goal:** Prepare for release
- Update `docs/sprint-6.md`
- Update README with new features
- Update CHANGELOG
- Evidence Pack

**Exit Criteria:**
- Documentation complete
- Release tag ready

---

## 13. Configuration Changes

Add to `configs/benchmark.yaml`:

```yaml
# Sprint 6: intelligent routing
routing:
  strategy: cost_aware  # cost_aware, capability_first, health_first, round_robin
  cost_ceiling: 0.0  # 0 = no limit
  fallback_enabled: true
  fallback_chain:
    - provider: openrouter
    - provider: huggingface
  circuit_breaker:
    enabled: true
    failure_rate_threshold: 0.5
    cooldown_seconds: 300
  parallel:
    enabled: false
    max_workers: 4
  preference:
    prefer_free: false
    min_capability_score: 0.7
```

### Validation Requirements
- `strategy` must be one of: cost_aware, capability_first, health_first, round_robin
- `cost_ceiling` must be float ≥ 0.0
- `fallback_chain` entries must reference registered providers
- `max_workers` must be int ≥ 1
- `failure_rate_threshold` must be float in [0.0, 1.0]
- All new keys have documented defaults; missing section loads with defaults

---

## 14. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Thread safety bugs in parallel executor | 🔴 Critical | Medium | Day 0: add locks to HealthTracker, HistoryWriter; stress-test before parallel code |
| Retry/fallback semantics confusion | 🔴 High | Medium | Explicit boundary documented in code; unit tests for each path |
| Engine modification regressions | 🔴 High | Low | Keep engine changes to strategy delegation only; regression tests |
| Circuit breaker excludes healthy provider transiently | 🟡 Medium | Low | Cooldown is bounded; health recovers automatically |
| Cost ceiling too strict for real-world scenarios | 🟡 Medium | Medium | Default is 0.0 (no limit); user-configurable |
| Benchmark idempotency violation in parallel | 🟡 Medium | Low | Audit benchmarks before parallel execution; block non-idempotent |
| SQLite corruption under concurrency | 🔴 High | Low | HistoryWriter serializes all writes; tested with concurrent stress |
| Strategy plugin registration failure | 🟢 Low | Low | Fallback to built-in default strategy if plugin load fails |
| Configuration validation gaps | 🟡 Medium | Medium | Validate routing section on load; clear error messages |
| Performance overhead from routing | 🟢 Low | Low | Selection is O(p × m × c); p=20, m=10, c=9 = 1800 ops |

---

## 15. Acceptance Strategy

### Functional Requirements
| Requirement | Verification Method |
|-------------|---------------------|
| LiteLLM config generation produces valid YAML | Unit test + schema validation |
| Model selection respects capabilities | Contract test per provider |
| Model selection respects health | Unit test with degraded provider |
| Model selection respects cost | Property-based test with cost ceiling |
| Fallback executes after retry exhaustion | Integration test with mock provider |
| Circuit breaker excludes failed provider | Unit test with failure threshold |
| Parallel execution yields same results | Comparison test vs sequential |
| History writes survive concurrent access | Stress test: 4 threads × 100 writes |
| CLI commands all functional | Smoke test per command |
| Backward compatibility maintained | Regression test suite |

### Non-Functional Requirements
| Requirement | Target |
|-------------|--------|
| Test coverage (new code) | ≥90% |
| Execution overhead from selection | <5% |
| Configuration load time | <100ms |
| CLI help response time | <50ms |

### Performance Requirements
| Metric | Baseline | Target |
|--------|----------|--------|
| BenchEngine.run_benchmark overhead | 0ms | <50ms |
| Model selection latency | N/A | <10ms |
| Fallback activation latency | N/A | <100ms |
| Parallel speedup (4 providers) | 1x | ≥1.5x |
| Concurrent history write throughput | N serial | ≥3x with 4 threads |

### Release Gates
1. All unit tests pass
2. All integration tests pass (or skipped with reason)
3. Coverage ≥90%
4. No hardcoded secrets
5. No broken imports
6. CLI smoke tests pass
7. Thread-safety stress tests pass
8. Documentation complete

---

## 16. Updated Sprint Structure

```
Sprint 6 (5 working days estimated)
├── Day 0: Concurrency Infrastructure
│   ├── HealthTracker thread-safety
│   ├── HistoryWriter serialization
│   └── Thread-safety tests
├── Day 1: Strategy Interfaces & Models
│   ├── RoutingContext, RoutingPlan, ExecutionPolicy
│   ├── BaseStrategy interface
│   └── Unit tests for new models
├── Day 2: Core Selection & Policy
│   ├── ModelSelector strategy plugin
│   ├── ExecutionPolicy strategy plugin
│   ├── Engine delegation wiring
│   └── Tests: selector, fallback, circuit breaker
├── Day 3: Parallel Execution
│   ├── ParallelExecutor implementation
│   ├── Rate-limit-aware scheduling
│   └── Tests: parallel correctness, thread safety
├── Day 4: Reports & CLI
│   ├── LiteLLM config reporter
│   ├── Routing reporter
│   ├── Optimization reporter
│   ├── CLI commands (6 new)
│   └── CLI smoke tests
└── Day 5: Integration, QA, Release Prep
    ├── Config validation schema
    ├── Full test suite
    ├── Coverage report
    ├── Documentation updates
    └── Evidence Pack
```

---

## 17. Estimated Complexity

| Component | Complexity | Risk | Lines of Code (est.) |
|-----------|-----------|------|---------------------|
| Concurrency infrastructure | Medium | High | 120 |
| Strategy interfaces & models | Low | Low | 100 |
| Model selector | Medium | Low | 200 |
| Execution policy | Medium | Medium | 200 |
| Parallel executor | High | Medium | 280 |
| LiteLLM config reporter | Medium | Low | 150 |
| Routing reporter | Low | Low | 100 |
| Optimization reporter | Low | Low | 100 |
| CLI commands | Low | Low | 200 |
| Config validation | Low | Low | 50 |
| Tests | Medium | Low | 500 |
| **Total** | | | **~2,050** |

### Complexity Distribution
- Low: 40%
- Medium: 45%
- High: 15%

### Scope Reduction Summary
- Removed: `cost_router.py` (150 LOC), `prompt_optimizer.py` (150 LOC)
- Moved: `litellm_config.py` to reporter (no LOC change)
- Replaced: `fallback.py` with `execution_policy.py` (net 50 LOC reduction)
- **Net reduction: ~400 LOC vs. original estimate**

---

## 18. Technical Debt Resolution

| Item | Action | Sprint |
|------|--------|--------|
| benchmark_version defaults to 0.4.0 | Update default and read from pyproject.toml | Sprint 6 |
| No CI/CD pipeline | Add GitHub Actions workflows | Sprint 6 |
| No GitHub Actions | Add test, lint, type-check, release workflows | Sprint 6 |
| HealthTracker not thread-safe | Add threading.Lock | Sprint 6 |
| HistoryWriter lacks serialization | Add HistoryWriter singleton with lock | Sprint 6 |

---

## 19. Final Recommendation

# 🟢 READY FOR ARCHITECTURE RE-REVIEW

### Verified Design Changes Incorporated

| Architecture Review Finding | Resolution |
|----------------------------|------------|
| No thread safety design | Designed `HealthTracker` lock + `HistoryWriter` lock + Day 0 infrastructure phase |
| `cost_router.py` duplicates `token_accounting.py` | Merged into `model_selector.py` |
| LiteLLM config in `app/` | Moved to `plugins/reporters/litellm_config.py` |
| Strategy plugin category unused | `ModelSelector` and `ExecutionPolicy` registered as `PluginCategory.STRATEGY` |
| Retry/fallback semantics conflated | Formal separation: engine owns retry, policy owns fallback + circuit breaker |
| `prompt_optimizer.py` scope creep | Deferred to Sprint 7 |
| Parallel target 2.5x unrealistic | Reduced to 1.5x with linear scaling trend |
| Engine modification vague | Engine delegates to strategy plugins via interface call |
| No config validation schema | Added validation requirements and explicit defaults |

### What Was Rejected

| Recommendation | Reason |
|----------------|--------|
| `BaseStrategy` with full execute interface | Over-designed for current scope; engine delegates directly to selector/policy instances. Strategy interface can be introduced when multiple strategy implementations exist. |
| `ParallelJob` abstraction | Unnecessary indirection. ParallelExecutor submits callables; each callable is a benchmark invocation. |

### Remaining Risks (Acceptable)

| Risk | Mitigation |
|------|------------|
| Thread-safety bugs | Day 0 stress tests before parallel code |
| Strategy plugin registration failure | Fallback to built-in defaults in engine |
| Circuit breaker transient exclusions | Bounded cooldown; automatic recovery |

### Baseline
**Development begins from:** `v0.5.0`
**Commit:** `88ef71d`
**Branch:** master

---

## 20. Previous Review Artifacts

- `docs/architecture/sprint-6-architecture-review.md` — Full architecture review with all findings
- `docs/sprint-6-plan.md` — This document

---

**Architecture Resolution Conclusion:** All verified architectural findings from the Architecture Review have been resolved. The Sprint 6 architecture is now coherent, module responsibilities are clearly defined, concurrency is explicitly designed, strategy plugin architecture is fully specified, retry and fallback semantics are separated, scope is controlled, and the benchmark engine remains a coordinator only. The plan is ready for independent Architecture Re-Review.
