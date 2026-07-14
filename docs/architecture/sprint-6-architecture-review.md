# Architecture Review Report — Sprint 6 Planning Document

**Project:** AI-Benchmark
**Baseline:** v0.5.0 (commit 88ef71d)
**Review Date:** 2026-07-13
**Review Type:** Independent Architecture Review
**Reviewer:** Architecture Review Board

---

## 1. Executive Summary

The Sprint 6 Planning Document proposes adding intelligent routing, automatic model selection, fallback strategies, cost-aware routing, parallel execution, and prompt optimization to AI-Benchmark. While the overall direction is valuable, the current design contains **critical architectural gaps** that must be resolved before implementation begins.

### Critical Findings
1. **Thread safety is unaddressed** — Parallel execution in a synchronous, global-state-heavy architecture requires explicit concurrency infrastructure that is absent from the plan.
2. **Module boundaries are confused** — `cost_router.py` duplicates `token_accounting.py`; `litellm_config.py` belongs in reporters, not `app/`.
3. **Strategy plugin category is unused** — Sprint 6 ignores the existing plugin extension point designed for this exact purpose.
4. **Engine modification is vague** — "Add routing hook" is insufficient design detail for modifying the core orchestration path.

### Verdict

# 🟡 ARCHITECTURE APPROVED WITH REQUIRED DESIGN CHANGES

The high-level direction is sound, but implementation must address thread safety, module boundaries, and plugin extension points before Day 1.

---

## 2. Baseline Architecture Review

### Core Components

| Component | Lines | Responsibility | Thread Safety |
|-----------|-------|----------------|---------------|
| BenchEngine | ~240 | Orchestrates benchmark runs | None |
| PluginManager | ~94 | Plugin lifecycle | Class-level attrs mutable |
| ProviderRegistry | ~154 | Provider discovery, health, metadata | None |
| HealthTracker | ~96 | Rolling-window health tracking | Global singleton, no locking |
| AppConfig | ~145 | YAML configuration | Mutable dict |
| CrossProviderBenchmark | ~93 | Sequential comparison | None |
| History | ~231 | SQLite persistence | WAL mode, no write coordination |

### Key Constraints Sprint 6 Must Preserve

1. **Synchronous-only execution model** — No `asyncio`, no threads, no process pools in Sprint 1-5.
2. **Global singletons** — `HealthTracker` and `PluginManager` are module-level singletons.
3. **Provider-agnostic engine** — `BenchEngine` contains zero provider-specific logic.
4. **Stateless benchmark plugins** — Each benchmark is a single-use object created per-run.
5. **SQLite for history** — WAL mode, but no concurrent writers.
6. **Entry-point-based plugin discovery** — No dynamic module loading beyond entry points.
7. **Provider interface is 22 methods** — Must remain unchanged.

### Baseline Strengths
- Clean separation: providers, benchmarks, evaluators, reporters
- Frozen dataclasses for immutable domain models
- Deterministic benchmark execution
- Retry logic embedded in engine with configurable policy
- Health tracking with rolling window averages

### Baseline Weaknesses Sprint 6 Must Not Propagate
- No concept of execution strategies (routing, fallback, selection)
- HealthTracker is not thread-safe
- SQLite writes block execution
- No circuit breaker or bulkhead patterns
- Cost estimation is naive (flat per-1k pricing)
- No execution plan abstraction

---

## 3. Sprint 6 Design Review

### 3.1 LiteLLM Configuration Generation

**Assessment:** ✅ VALID but misplaced

**Purpose:** Generate LiteLLM-compatible YAML from provider capabilities, health, metadata, cost, and auth.

**Problems:**
- Placing this in `app/litellm_config.py` bloats the core application layer with an external integration concern.
- LiteLLM config generation is a **report/reporter** activity — it transforms internal state into an external format.
- Should be `plugins/reporters/litellm_config.py` or similar.

**Recommendation:**
- Move to `plugins/reporters/litellm_config.py`
- Register as a reporter plugin
- Accept same inputs as other reporters (results, registry, config)
- No modification to `models.py`

### 3.2 Intelligent Model Selection

**Assessment:** ⚠️ VIABLE with major design gaps

**Purpose:** Automatic model selection based on category requirements, capabilities, health, cost, and historical performance.

**Problems:**
- No interface/abstraction defined for `ModelSelector`.
- Direct integration with `ProviderRegistry` creates tight coupling.
- Historical performance integration with SQLite history is undefined (queries, schema, freshness).
- "Deterministic output with fallback to configured default" — needs explicit tie-breaking rules.
- No consideration for context window alignment (Prompt Optimizer is a separate module, but selection should already account for context).

**Recommendations:**
- Define `ModelSelector` as a **strategy plugin** (use existing `PluginCategory.STRATEGY`).
- Accept `RoutingPolicy` and `RoutingContext` dataclasses as inputs.
- Tie-breaking rules must be explicit in implementation, not left to "deterministic output" claims.
- Selection should include context-window feasibility check from `ProviderCapabilities.context_window`.

### 3.3 Fallback Strategies

**Assessment:** ⚠️ ARCHITECTURAL RISK

**Purpose:** Provider alternation, model alternation, category fallback, enhanced retry.

**Problems:**
1. **Conflates retry and fallback.** The engine already retries the same provider/model. Fallback switches provider/model. These must be cleanly separated or users will experience unpredictable behavior.
2. **Category fallback breaks determinism.** If category A fails and gets skipped, the result set changes shape. This affects scoring, history, and comparison reports.
3. **Stateful benchmark risk.** If a benchmark has side effects (e.g., headers tracked in history), retrying could double-count.
4. **No circuit breaker.** The plan doesn't mention avoiding known-bad providers based on recent failures.

**Recommendations:**
- Rename to `ExecutionPolicy` to encompass retry + fallback + circuit breaking.
- Retry: same endpoint, transient failures (timeout, 429, 5xx).
- Fallback: alternate endpoint/model, structural failures (401, 404, capability mismatch).
- Category fallback should produce a `BenchmarkResult` with explicit `status="skipped"` rather than omitting it.
- Add circuit breaker: exclude providers with `failure_rate > 0.5` from selection for a cooldown period.

### 3.4 Cost-Aware Routing

**Assessment:** ❌ PROBLEMATIC — overlaps with existing code

**Purpose:** Route to cheapest qualified provider/model; threshold-based routing; budget enforcement.

**Problems:**
1. **Duplicates `token_accounting.py`.** The plan says "extend existing `app/token_accounting.py`" but also creates `app/cost_router.py`. This is conflicting and suggests module boundary confusion.
2. **Cost data is already in `BenchEngine._populate_metadata`.** Adding another cost estimator creates redundancy.
3. **"Threshold-based routing: if cost delta < X%, prefer higher capability"** — this is a model selection concern, not a routing concern. It should be a selection strategy parameter.

**Recommendation:**
- Merge `cost_router.py` into `model_selector.py` as one strategy parameter set.
- Cost data flows from `AppConfig.model_cost()` → selector uses it → engine estimates cost post-run.
- No separate module needed.

### 3.5 Multi-Provider Parallel Execution

**Assessment:** 🔴 HIGH RISK — requires significant infrastructure

**Purpose:** Execute independent benchmarks across multiple providers simultaneously.

**Problems:**
1. **Thread safety entirely unaddressed.** HealthTracker uses `deque` without locking. SQLite connections are not thread-safe by default. PluginManager class attributes are mutable.
2. **Rate limit awareness is circular.** The plan says "respect per-provider health/rate-limit data" but healthy-looking providers can still exhaust bursts in parallel.
3. **Result ordering requires deterministic aggregation.** Parallel execution changes observation order — this must be handled explicitly.
4. **No isolation boundary.** If provider A writes to history and provider B fails, partial state must be handled.

**Recommendations:**
- Paralellism must be **opt-in via config flag**, not default.
- Introduce `ExecutionResultCollector` as an isolation boundary for parallel runs.
- HealthTracker must add `threading.Lock` around `_samples` and `_states` mutations.
- SQLite writes must use a connection pool or be serialized via a `HistoryWriter` lock.
- Benchmarks must be verified as idempotent before parallel execution is allowed.
- Realistic performance target: **1.5x speedup**, not 2.5x. Network bounds make 2.5x unrealistic.

### 3.6 Provider-Specific Prompt Optimization

**Assessment:** ⚠️ SCOPE CREEP

**Purpose:** Adjust prompt parameters per provider (temperature, max tokens, formatting, context window).

**Problems:**
1. **Doubles the prompt matrix.** Current: 9 prompts. With provider variants: 9 × 4 providers = 36 prompts minimum.
2. **Provider-specific formatting is provider responsibility.** Each provider plugin knows how to format requests. Prompt optimization should happen in the provider, not the engine.
3. **"Context window alignment"** should be handled at selection time (ModelSelector), not prompt time.

**Recommendation:**
- **Defer to Sprint 7.** This feature adds configuration complexity without proportional value.
- If included later, implement as provider plugin method: `provider.optimize_prompt(prompt, model) → optimized_prompt`.
- Keep prompts provider-agnostic; let providers format context.

### 3.7 Configuration Changes

The plan adds ~15 new keys under `routing:` in `configs/benchmark.yaml`. This is acceptable but needs:
- **Validation layer.** `AppConfig` currently has no schema validation beyond Pydantic's implicit dict typing. New keys must be validated at load time with clear error messages.
- **Defaults must be explicit.** Every new key must have a documented default value.

---

## 4. Module Review

### Module-by-Module Assessment

| Proposed Module | Purpose | SRP | Coupling | Placement | Verdict |
|-----------------|---------|-----|----------|------------|---------|
| `app/litellm_config.py` | LiteLLM YAML generation | ✅ Good | High (needs registry, config, all providers) | ❌ Wrong — should be reporter plugin | **Move to reporter** |
| `app/model_selector.py` | Auto model selection | ✅ Good | High (needs registry, capabilities, health, history) | ✅ Correct | **Approved with stratey plugin** |
| `app/fallback.py` | Fallback execution | ⚠️ Moderate | Medium (needs engine, registry) | ⚠️ Should merge with retry | **Refactor as ExecutionPolicy** |
| `app/cost_router.py` | Cost-aware routing | ❌ Overlaps | High (duplicates token_accounting) | ❌ Unnecessary | **Merge into model_selector** |
| `app/parallel_executor.py` | Parallel execution | ⚠️ Broad | High (needs engine, history, health, registry) | ⚠️ Consider as strategy plugin | **Approved with thread-safety fixes** |
| `app/prompt_optimizer.py` | Provider prompt tuning | ⚠️ Scope creep | Medium (needs prompts, provider config) | ❌ Defer to Sprint 7 | **Defer** |
| `plugins/reporters/routing.py` | Routing report | ✅ Good | Medium | ✅ Correct | **Approved** |
| `plugins/reporters/optimization.py` | Optimization report | ✅ Good | Medium | ✅ Correct | **Approved** |

### Modified Modules Risk Assessment

| Modified Module | Risk | Notes |
|-----------------|------|-------|
| `app/engine.py` | 🔴 HIGH | Run_benchmark is 110 lines of core logic. Adding routing hooks changes control flow significantly. |
| `app/config.py` | 🟡 MEDIUM | Adding 15+ keys needs validation schema. |
| `app/models.py` | 🟡 MEDIUM | Adding RoutingPlan, FallbackChain, OptimizationResult is fine, but models.py is already 427 lines. Consider `app/models/routing.py` split if exceeds 500 lines. |

---

## 5. Interface Review

### Existing Extension Points

Sprint 5 introduced a `PluginCategory.STRATEGY` — exactly designed for execution strategy plugins. Sprint 6 ignores this.

**Critical Recommendation:** Use `PluginCategory.STRATEGY` for:
- `ModelSelector` → register as strategy plugin
- `FallbackStrategy` → register as strategy plugin
- `CostRoutingStrategy` → register as strategy plugin

This provides:
- Runtime strategy swapping via `PluginManager.set_enabled()`
- Priority-based selection via `PluginManager.set_priority()`
- No hardcoding in engine

### What New Interfaces Are Needed

| Interface | Purpose | Required |
|-----------|---------|----------|
| `RoutingContext` | Encapsulate benchmark requirements, constraints, preferences | ✅ Yes — model selector input |
| `RoutingPlan` | Selection decision + rationale + fallback candidates | ✅ Yes — model selector output |
| `ExecutionPolicy` | Retry + fallback + circuit breaker rules | ✅ Yes — replace fallback module |
| `ParallelJob` | Isolated benchmark execution unit | ✅ Yes — parallel executor needs clear boundary |

### What Is NOT Needed

- No new provider interface methods
- No new benchmark interface methods
- No new reporter interface methods

---

## 6. Scalability Assessment

### Provider Count (Current: 4, Target: 20+)

| Concern | Current State | Sprint 6 Impact | Mitigation |
|---------|--------------|-----------------|------------|
| Provider lookup | O(n) dict scan | Unchanged | Registry is O(1) dict |
| Health tracking | O(1) per record | Unchanged | Rolling window is fixed-size |
| Capability matching | O(n) scan | Unchanged | 13 flags, constant time |
| Model selection | N/A | O(p × m) per category | Acceptable; p=20, m=10, categories=9 = 1800 ops |

### Model Count (Current: ~4 per provider, Target: 100+)

| Concern | Current State | Sprint 6 Impact | Mitigation |
|---------|--------------|-----------------|------------|
| list_models | Live API call | Unchanged | Registry caches results |
| Cost lookup | Dict in YAML | O(m) scan | Struct: `{provider: {model: {p, c}}}` |
| Capability mapping | Static detection | O(m) | Capabilities are provider-level, not model-level |

### Routing Policies (Proposed: 4)

The plan proposes 4 strategies: cost_aware, capability_first, health_first, round_robin. This is fine.

But **hybrid strategies** are not addressed. A realistic system needs composite strategies like "health_first + cost_tiebreaker". This should be addressed in the strategy interface design.

### Bottleneck Analysis

| Bottleneck | Severity | Cause | Mitigation |
|------------|----------|-------|------------|
| HealthTracker singleton | 🔴 High | No locking; parallel writes corrupt state | Add `threading.Lock` |
| SQLite writes | 🔴 High | No concurrent write support | Serialize via `HistoryWriter` lock |
| Provider instantiation | 🟡 Medium | `_init_provider` creates new instance per call | Cache provider instances (but careful with state) |
| Prompt loading | 🟡 Medium | File I/O on every benchmark | Cache in `PromptLoader` |
| Cost estimation | 🟢 Low | Simple arithmetic | No change needed |

---

## 7. Reliability Assessment

### Fallback Logic

**Current Problem:** The plan conflates retry and fallback.

**Required Separation:**
- **Retry** (engine's responsibility): Same endpoint, transient failure, bounded attempts, exponential backoff.
- **Fallback** (policy's responsibility): Alternate endpoint/model, structural failure, circuit-breaker awareness.

**Current Engine Retry Logic:**
```python
# From engine.py:166-192
while True:
    attempt += 1
    try:
        response = provider.chat(model, messages, **kwargs)
        break
    except Exception as exc:
        if not retryable(exc):
            break
        if attempt > retry_count:
            break
        sleep(backoff)
```

**Fallback must happen AFTER retry exhaustion**, not as a replacement for retry.

### Parallel Execution

**Deadlock Risk:** Medium-High
- HealthTracker lock + SQLite lock + provider instance lock could deadlock.
- Solution: single `HistoryWriter` with its own lock; always acquire locks in fixed order.

**Race Condition Risk:** High
- `HealthTracker._samples` is a `dict[str, deque]` — concurrent `append` on `deque` is not thread-safe.
- `ProviderHealth._states` dict mutations must be atomic.

**State Leakage Risk:** Medium
- Provider instances created in parallel threads may share session state (cookies, connections).
- Each parallel job must use a fresh provider instance.

### Timeout Management

Current: single request timeout per benchmark.
Parallel: 4 providers × 4 benchmarks = 16 concurrent requests. Per-benchmark timeout still applies, but total wall clock time could be minutes. This needs explicit `max_duration` for the entire parallel job.

---

## 8. Testability Assessment

### Unit Testing Feasibility

| Component | Testability | Main Challenge |
|-----------|------------|----------------|
| model_selector.py | ✅ Good | Mock registry, health, config |
| ModelSelector strategies | ✅ Good | Pure function with mocked inputs |
| fallback.py / ExecutionPolicy | ⚠️ Moderate | Needs failure injection hooks |
| parallel_executor.py | 🔴 Difficult | Thread timing, race conditions |
| parallel_executor correctness | ✅ Good (comparison) | Compare parallel vs sequential results |
| litellm_config.py | ✅ Good | Schema validation against known config |
| prompt_optimizer.py | N/A | Deferred to Sprint 7 |

### Integration Testing Strategy

| Test Scenario | Approach |
|---------------|----------|
| Selection + registry | Contract test: selector returns valid model from registry |
| Fallback with mock failures | Custom mock provider that fails N times, succeeds on N+1 |
| Parallel correctness | Run same benchmarks sequentially and in parallel; assert identical results |
| Thread safety | Run 100 parallel health checks; assert no exceptions |
| SQLite concurrent writes | 4 threads writing 100 records each; assert no corruption |

### Mocking Requirements

- mock `ProviderRegistry` for selector tests
- mock `AppConfig` for all new modules
- mock `BenchEngine` for parallel executor tests
- mock `HistoryWriter` for parallel write tests

### Coverage Feasibility

- New code: ~2,450 LOC estimated
- 90% coverage target on new code is realistic
- Parallel executor is the hardest to cover comprehensively
- Mock-based unit tests for selector, fallback, config generation are straightforward

---

## 9. Backward Compatibility Review

### CLI Compatibility

| Change | Impact |
|--------|--------|
| 6 new CLI commands | ✅ No breaking changes |
| New commands grouped under `benchmark route` | ⚠️ The plan doesn't specify grouping. If they're top-level (e.g. `benchmark optimize`, `benchmark parallel`), that's fine. If they're subcommands of `benchmark route`, also fine. Just be consistent. |

### Configuration Compatibility

New `routing:` section with defaults. Existing `configs/benchmark.yaml` without `routing:` must load without errors.

**Requirement:** `AppConfig` must handle missing optional sections gracefully.

### Provider Compatibility

Zero changes to `BaseProvider` interface or provider plugins. ✅

### Benchmark Compatibility

Zero changes to `BaseBenchmark` interface or benchmark plugins. ✅

### Report Compatibility

Existing reports (json, md, csv, sprint4) unchanged. New reports added. ✅

### History Compatibility

`HistoryWriter` must support concurrent writes if parallel execution is enabled. Currently no concurrency support. This is a **modifying dependency** — sprint 6 needs to update `app/history.py`.

---

## 10. Technical Debt Review

### Should Sprint 6 Resolve?

| Debt Item | Recommended Sprint | Rationale |
|-----------|-------------------|-----------|
| benchmark_version defaults to 0.4.0 | **Sprint 6** | Directly affects routing/config accuracy. Low effort, medium value. |
| No CI/CD pipeline | **Sprint 6** | Low effort, blocks contribution workflow. Should be Day 1. |
| No GitHub Actions | **Sprint 6** | Part of CI/CD. |
| Pre-existing mypy/ruff issues | Sprint 7+ | Out of scope. |
| `enabled`/`priority`/`aliases` not enforced | Sprint 7 | Low value. |
| CLI duplication | Sprint 7 | Low value. |

### Technical Debt the Plan Should Add

1. **Thread-safety debt** — `HealthTracker`, `PluginManager`, `HistoryWriter` need locking. This is new debt Sprint 6 must incur.
2. **Interface debt** — Routing/selection/fallback lack interfaces. Must define before implementation.
3. **Test debt** — Parallel execution requires race-condition testing infrastructure not currently present.

---

## 11. Alternative Architectures Considered

### Alternative A: Strategy Plugin Composition (RECOMMENDED)

**Design:** Implement routing, selection, and fallback as `PluginCategory.STRATEGY` plugins. Engine delegates to strategy plugin at execution time.

| Feature | Advantage | Disadvantage |
|---------|-----------|-------------|
| Runtime strategy swapping | ✅ Users can change strategies via config | Slightly more complex registration |
| Priority ordering | ✅ Users can define fallback chains via priority | Requires priority enforcement in engine |
| Isolation | ✅ Each strategy is independently tested | One more indirection layer |

**Why it's preferable:** Uses existing extension point. No engine modifications beyond one delegation call. Clean separation of concerns.

### Alternative B: Engine-Level Monolithic Integration (CURRENT PLAN)

**Design:** Add routing/fallback/selection code directly into BenchEngine.

| Feature | Advantage | Disadvantage |
|---------|-----------|-------------|
| Direct control | ✅ No indirection | ❌ Engine becomes god class |
| Tight coupling | ✅ Easy to implement | ❌ Hard to test, extend, override |
| Performance | ✅ Minimal call overhead | ❌ Marginal gain vs strategy overhead |

**Why it's inferior:** Violates SRP. Engine already handles retry, timeout, cost, health, metadata, report generation. Adding routing compounds this.

### Alternative C: External Decision Service

**Design:** Run routing/selection as a separate process/service.

| Feature | Advantage | Disadvantage |
|---------|-----------|-------------|
| Isolation | ✅ Crashes don't affect engine | ❌ Overkill for this scope |
| Scalability | ✅ Can scale independently | ❌ Adds deployment complexity |
| Testability | ✅ Black-box testing | ❌ IPC complexity |

**Why it's inferior:** Premature optimization. The project doesn't need distributed architecture yet.

### Alternative D: Rule-Based Configuration Only (SIMPLER)

**Design:** Instead of intelligent selection, provide `routing:` configuration that maps categories to providers/models.

| Feature | Advantage | Disadvantage |
|---------|-----------|-------------|
| Simplicity | ✅ Zero runtime overhead | ❌ Less intelligent |
| Determinism | ✅ Config is the plan | ❌ No health awareness |
| Testability | ✅ Trivial | ❌ Users must maintain mappings |

**Why it's inferior:** Removes the "intelligent" from intelligent routing. Not worth implementing if the system can't make decisions based on health.

---

## 12. Risk Matrix

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Thread safety bugs in parallel executor | 🔴 Critical | High | Add locks to HealthTracker, HistoryWriter, SQLite before parallel code |
| Retry/fallback semantics confusion | 🔴 High | High | Define explicit boundary in design; document in code |
| Engine modification regressions | 🔴 High | Medium | Keep engine changes minimal; use strategy delegation |
| Configuration complexity overload | 🟡 Medium | Medium | Validate config on load; document every key with defaults |
| Benchmark bias from routing | 🟡 Medium | Low | Deterministic routing; audit trail in results |
| Cost estimation inaccuracy | 🟡 Medium | Medium | Report estimates as estimates, not facts |
| LiteLLM config drift | 🟡 Medium | Low | Treat LiteLLM config as generated artifact, not source of truth |
| Stateful benchmark breakage | 🟡 Medium | Medium | Audit all benchmarks for idempotency; block parallel for non-idempotent |
| SQLite corruption under concurrency | 🔴 High | Medium | Serialize all DB writes via `HistoryWriter` singleton |
| Performance overhead from routing | 🟢 Low | Low | Routing is O(p × m × c) — p=20, m=10, c=9 = 1800 ops |

---

## 13. Recommended Design Changes

### CRITICAL (Must Resolve Before Day 1)

1. **Thread Safety Infrastructure**
   - Add `threading.Lock` to `HealthTracker` for `_samples` and `_states`.
   - Add `HistoryWriter` singleton with write serialization for SQLite.
   - Provider instances must not be shared across threads.

2. **Strategy Plugin Architecture**
   - Move `model_selector`, `fallback`, and routing logic into `PluginCategory.STRATEGY`.
   - Engine delegates to strategy plugins via one interface method.
   - This preserves engine cleanliness.

3. **Eliminate cost_router.py**
   - Merge into `model_selector.py`. Cost is a selection input, not a routing layer.

### HIGH (Must Resolve Before Phase 2)

4. **Clear Retry/Fallback Separation**
   - Retry stays in engine (unchanged).
   - Fallback becomes `ExecutionPolicy` strategy, invoked after retry exhaustion.
   - Circuit breaker is part of `ExecutionPolicy`.

5. **Execution Boundaries for Parallel**
   - Define `ParallelJob` as isolated execution unit.
   - Each job gets fresh provider instance, isolated result set.
   - Jobs cannot mutate shared state except through locked channels.

### MEDIUM (Should Resolve Before Phase 3)

6. **Move LiteLLM Config to Reporter**
   - `plugins/reporters/litellm_config.py` — not `app/`.

7. **Config Validation Schema**
   - Add explicit validation schema for `routing:` keys.
   - Document defaults in `configs/benchmark.yaml` comments.

8. **Defer Prompt Optimizer**
   - Move to Sprint 7. Not proportional value for Sprint 6 scope.

### LOW (Should Resolve Before Phase 5)

9. **CLI Command Grouping**
   - Group new commands: `benchmark route`, `benchmark select`, `benchmark fallback`, `benchmark optimize`, `benchmark parallel`, `benchmark config generate-litellm`.
   - Current plan lists them as top-level commands. Grouping improves discoverability.

10. **Realistic Parallel Performance Target**
    - Change from "≥2.5x speedup" to "≥1.5x speedup with linear scaling trend."
    - Document network I/O bound behavior.

---

## 14. Final Recommendation

# 🟡 ARCHITECTURE APPROVED WITH REQUIRED DESIGN CHANGES

### What Is Approved

| Component | Version |
|-----------|---------|
| Intelligent model selection | ✅ With strategy plugin interface |
| Fallback strategies | ✅ With clear retry/fallback separation |
| Cost-aware selection | ✅ Merged into selector |
| LiteLLM config generation | ✅ As reporter plugin |
| Parallel execution framework | ✅ With thread-safety infrastructure |
| Reporting additions | ✅ routing.py, optimization.py |

### What Must Change Before Implementation

| Change | Owner | Priority |
|--------|-------|----------|
| Thread-safety: HealthTracker, HistoryWriter, SQLite | Architect | Day 0 |
| Strategy plugin architecture for selection/fallback | Architect | Day 1 |
| Eliminate cost_router.py; merge into model_selector | Architect | Day 1 |
| Move litellm_config.py to reporters | Architect | Day 1 |
| Defer prompt_optimizer.py to Sprint 7 | Architect | Day 0 |
| Define retry/fallback boundary explicitly | Architect | Day 1 |
| Add config validation for routing keys | Developer | Day 2 |
| Realistic parallel speedup target (1.5x) | Architect | Day 0 |

### What Must NOT Be Implemented

| Item | Reason |
|------|--------|
| Direct engine modifications for routing | Use strategy plugin delegation |
| New cost estimation in cost_router.py | Duplicates existing logic |
| Provider-specific prompt templates | Defer to Sprint 7 |
| Agent orchestration | Out of scope |

### Architecture Verdict

The Sprint 6 **goal is architecturally sound**: adding intelligent decision-making atop the provider platform established in Sprint 5. However, the **current detailed design requires refinement** in four areas:

1. **Concurrency infrastructure** — thread safety must be designed in from Day 0, not retrofitted.
2. **Module boundaries** — cost_router shouldn't exist; LiteLLM config shouldn't be in `app/`.
3. **Plugin architecture** — strategy plugins must be used, not ignored.
4. **Engine preservation** — BenchEngine must remain clean; delegation is the pattern.

### Recommended Immediate Actions

1. Architect updates `docs/sprint-6-plan.md` with revised module list and interfaces.
2. Create `docs/architecture/strategy-interface.md` defining `RoutingStrategy`, `FallbackStrategy`, `ExecutionPolicy`.
3. Create `docs/architecture/thread-safety.md` defining locking boundaries.
4. Re-review the updated plan with this board before implementation begins.

---

**Architecture Review Conclusion:** Sprint 6 is conceptually approved but requires design refinement in four critical areas before implementation. The board is available for a follow-up design review once changes are incorporated.
