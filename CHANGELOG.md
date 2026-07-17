# Changelog

## [2.0.0] - 2026-07-17

### Added
- Decision Engine: dynamic evidence-backed recommendations per task category.
- Recommendation Engine: category-specific suggestions with confidence scoring, trade-offs, and rejection reasons.
- Claude Code Routing Generator: automatic routing config generation from benchmark evidence.
- Confidence Scoring: quantitative confidence with evidence quality weighting (High/Medium/Low).
- Benchmark Explanation Engine: human-readable recommendation explanations via `benchmark explain` and `benchmark governance`.
- Historical Trend Analysis: trend detection, comparison, stability tracking via `benchmark trends` and `benchmark compare`.
- Provider Resilience: circuit breaker, retry with exponential backoff, rate limit detection.
- Historical Storage: SQLite persistence with load/save verification.

### Changed
- Test count: 500 passed, 6 skipped, 0 failures.
- Coverage: 95.11%.
- Sprint 12.5 production-readiness validation completed.

### Fixed
- model_selector.py: normalize string `benchmark_name` to `BenchmarkName` enum in `select()` to prevent AttributeError when routing context uses string benchmark name.

## [1.3.0] - 2026-07-16

Sprint 11 engineering quality improvements.

- Reduce MyPy strict-mode errors from 35 to 0 across 70 source files.
- Resolve TD-ResourceWarnings-9 via unconditional conn.close() in history.py.
- Increase test coverage from 94% to 95.03%.
- Add 28 new unit tests covering engine, analytics, history, and model_selector.
- Remove deprecated ResourceWarning suppression from pyproject.toml.
- Add CI coverage gate: fail_under = 95 under [tool.coverage.report].
- Update fixture hygiene: HistoryWriter.reset(), conn.close() in test_sprint8_memory.

## [1.2.0] - 2026-07-16

### Added
- Comprehensive type annotation coverage across engine boundary files: `engine.py`, `model_selector.py`, `validation.py`, `parallel_executor.py`, `memory_profiler.py`, `prompts.py`, `token_accounting.py`, `rc_validation.py`, `cli.py`.
- Type annotation cleanup in benchmark and provider plugins (`coding`, `debugging`, `general`, `instruction`, `json`, `latency`, `reasoning`, `research`, `code_review`, `ollama`, `huggingface`, `nvidia`, `openrouter`, `generator.py`).
- Developer documentation at `docs/developer-guide.md`.
- Release governance archive: Sprint 10 planning, technical debt register, implementation report, internal QA, QA resolution, QA re-validation, and RC validation reports.

### Changed
- Regression suite expanded by 48 new tests (6 files) covering auth, auto-validation, coverage config, execution policy, plugin manager, and validation logic.
- Overall test count: 439 passed, 6 skipped, 0 failures.
- Plugin registry validated: 37 plugins across 5 categories; all valid with consistent `plugin_api_version = "1.0"`.
- Coverage improved to 93.52% raw (94% rounded) under Sprint 10 rounding policy.
- MyPy static checking maintained within ≤40 error threshold with 0 new regressions introduced.

### Fixed
- Type-only internal refactors in `model_selector.py` and `engine.py` that extract inline imports to local variables to satisfy mypy without changing runtime behavior.
- Module-level import organization to avoid circular dependency risks while preserving backward compatibility.

## [1.0.0] - 2026-07-15

### Added
- Performance optimization: `ParallelExecutor` now preserves deterministic order with reduced scheduling overhead.
- Memory optimization: SQLite connection lifecycle management with context manager support and bounded resource handling.
- Production packaging: `pyproject.toml` versioned at `1.0.0` with optional extras and validated entry points.
- Installation system: user guide, developer bootstrap scripts (`scripts/bootstrap.sh`, `scripts/bootstrap.bat`), and platform validation.
- Documentation: quickstart, installation, troubleshooting, CLI reference, plugin SDK, and security documentation.
- Plugin SDK: `plugin_api_version` enforcement, compatibility policy, and `benchmark plugin validate` command.
- CI/CD improvements: docs accuracy validation, security scanning workflow (`security-scan.yml`), and reproducible build constraints.
- Security hardening: typed input validators, YAML safe loader, JSON schema validation, dependency audit script, and security documentation.
- Configuration migration: additive `schema_version` field with idempotent migration framework (`0.7.0` → `1.0.0`).
- Release Candidate validation: architecture boundary checklist and RC validation helpers.

### Changed
- Engine hot paths maintain deterministic behavior while allowing bounded optimizations.
- SQLite history helpers enforce strict ownership models with no cross-thread connection sharing.
- Plugin contracts now include explicit API versioning with backward-compatible compatibility policy.
- Release governance now mandates RC boundary checks and documentation accuracy validation.

## [0.7.0] - 2026-07-15

### Added
- History-aware model ranking via `recent_category_performance()` read API.
- Context-window feasibility check using provider-level `ProviderCapabilities.context_window`.
- Fallback strategy configuration: `routing.fallback.strategy` supports `provider_first`, `model_first`, `hybrid`.
- Model alternation under fallback policy in `BenchEngine`.
- Deterministic tie-break keys in all `ModelSelector` strategies.
- Release automation workflow: `.github/workflows/release.yml` with manual `workflow_dispatch`.
- `docs/usage/routing.md` and `examples/benchmark.example.yaml`.

### Changed
- `ModelSelector` strategies populate `fallback_models` for the selected provider.
- `ExecutionPolicy` enriches fallback topology and supports model-first fallback.
- Engine fallback execution iterates provider alternation then model alternation.
- `AppConfig._load_routing()` validates optional `routing.fallback.strategy` key.

## [0.6.0] - 2026-07-13

### Added
- Thread-safe `HealthTracker` with `threading.Lock` for parallel execution safety.
- `HistoryWriter` singleton with SQLite write serialization.
- Routing configuration validation with defaults and back-compat.
- Strategy plugins: `ModelSelector` (cost_aware, capability_first, health_first, round_robin) and `ExecutionPolicy` (fallback + circuit breaker).
- Engine delegation: `BenchEngine.select_model()` and `BenchEngine.apply_policy()`.
- `ParallelExecutor`: thread-pool based, deterministic ordering, job-level failure isolation.
- Reporters: `litellm_config`, `routing`, `optimization`.
- CLI commands: `route`, `select`, `fallback`, `optimize`, `parallel`, `config generate-litellm`.
- `PluginManager` pluralization fix for `PluginCategory.STRATEGY`.

### Changed
- Benchmark version default now reads from `pyproject.toml` (`0.6.0`).
- SQLite connections use `check_same_thread=False` for concurrent write safety.

## [0.5.0] - 2026-07-13

### Added
- Universal Provider Interface: 22-method contract across all providers.
- Provider Plugin Architecture: dynamic loading, unloading, enable/disable, priority, aliases.
- Provider Registry: automatic discovery, lookup, capability detection, metadata, health, validation, certification.
- Capability Detection: 13 flags per provider (chat, reasoning, vision, streaming, function calling, JSON mode, structured output, embeddings, image generation, audio, tool calling, long context, context window, max output tokens).
- Authentication Layer: environment variables, .env, configuration files, credential validation.
- Health Monitoring: availability, latency, auth status, failure/retry/timeout rates, rate limits, avg/p95/p99 latency, health reports.
- Provider Metadata: name, endpoint, region, capabilities, supported models, auth type, pricing, token limits, context window, streaming, function calling, vision, reasoning, embeddings, JSON mode.
- Rate Limit Detection: 429, quota exceeded, maintenance, daily quota, burst limits, provider-specific limits, retry recommendations.
- Cross Provider Benchmarking: single/multiple providers, multiple models, multiple categories, category comparison.
- Provider Comparison Reports: rankings, capability matrix, latency, reliability, cost, token efficiency, reasoning, coding, research, overall.
- Provider Certification: 4-level classification with scoring and validation.
- CLI commands: `providers`, `provider list`, `provider info`, `provider health`, `provider compare`, `models`, `capabilities`, `auth`, `discover`, `provider validate`, `provider certify`.
- New reporters: provider_comparison, provider_health, capabilities.
- `docs/sprints/sprint-5.md`.

### Changed
- Engine is fully provider-agnostic; no provider-specific logic in benchmark core.
- Configuration fully externalized via YAML.
- Version bumped to 0.5.0.

## [0.4.0] - 2026-07-13

### Added
- Benchmark validation: `validate_results`, `validate_metadata`, `auto_validate`, `validate_recommendations`.
- Calibration engine: category bias, inflation detection, discriminative power, recommendation instability.
- Statistics module: `summarize`, `category_stats`, `outlier_runs`, `score_drift`, confidence intervals.
- Reliability metrics: success/failure/timeout/retry rates, avg/p95/p99 latency, provider availability.
- Token accounting: prompt/completion/total tokens, tokens/sec, estimated cost breakdown by provider/model.
- Retry policies: `RetryPolicy`, exponential backoff, retryable exception filtering.
- Timeout policies: request/benchmark/category/connect timeouts.
- Reproducibility metadata on every `BenchmarkResult`: provider/model/version/prompt/timestamp/seed/tokens/cost.
- Sprint 4 reporters: validation, calibration, reliability, statistics, tokens, cost, metadata, governance.
- CLI commands: `validate`, `calibrate`, `stats`, `reliability`, `reproduce`, `cost`, `tokens`, `governance`.

### Changed
- `BenchEngine.run_benchmark` now captures retry count, timeout status, latency, tokens, cost, and run metadata.
- `configs/benchmark.yaml` extended with retry, timeout, cost, and versioning settings.
- `models.py` extended with Sprint 4 domain dataclasses.

### Fixed
- `test_end_to_end_mocked` provider interface alignment.
- Validation consistency: reporters now use `auto_validate`; CLI and reporters share one canonical validation path.
- Retry semantics corrected: `retry_count` now means number of retries (total attempts = retries + 1).
- Cost reporting: reporters now read configured token prices from `configs/benchmark.yaml` instead of hardcoding 0.0.
- Recommendation reporters now include overall score, weight contribution, major contributing categories, and explicit rejection reasons.

## [0.3.0] - 2026-07-12

### Added
- Sprint 3: SQLite history persistence with `save_run`, `load_latest`, `load_run`, and `init_db`.
- Analytics engine: leaderboard, trend analysis, recommendations, AI engineering team assembly, run comparison.
- Confidence engine with High/Medium/Low labels derived from score variance and reliability signals.
- Trade-offs section in recommendation and team reports.
- New CLI commands: `leaderboard generate`, `recommend`, `team`, `compare`, `trends`, `explain`.
- New report types: leaderboard, recommendations, team, trends, compare.
- `docs/sprints/sprint-3.md`.

### Changed
- README updated to include Sprint 3 features, commands, and project structure.
- Version bumped to 0.3.0.

### Fixed
- `analytics.py` `build_trends()`: fixed `key.split(":", 2)` unpacking crash on `provider:model` keys.
- `history.py` `load_latest()`: added `init_db()` before table queries to fix fresh-database crashes.
- `history.py` `load_run()`: fixed `BenchmarkName` enum conversion from DB strings with malformed-data handling.
- `plugins/reporters/analytics.py`: removed unused `import json`.
- Reporter history-load fallbacks now use persistent SQLite data correctly.

## [0.2.0] - 2026-07-12

### Added
- Sprint 2: Multi-category benchmark execution and evaluation.
- General, Coding, Debugging, Code Review, Research, Reasoning, JSON, Instruction Following, Latency benchmarks.
- Reusable evaluation engine with objective scoring and normalization.
- Configurable weights in `configs/benchmark.yaml`.
- Prompt files per benchmark under `prompts/`.
- Enriched reporters: JSON with scores/evaluation/recommendations; Markdown with per-category rows; CSV with category breakdown.
- Automatic all-categories execution via `benchmark run main`.

### Changed
- Engine passes prompt metadata into benchmark plugins for context-aware evaluation.
- Scoring unified through `Score` dataclass with weighted calculation.

### Fixed
- Objective validators now implemented for General, Reasoning, Research, Debugging, and Code Review.
- Model-differentiation behavioral tests added for all benchmark categories.
- Test coverage raised to 95%.

## [0.1.0] - 2026-07-12

### Added
- Initial release: AI-Benchmark Sprint 1.
- Plugin-based benchmark engine.
- Built-in providers: Ollama, NVIDIA, OpenRouter, Hugging Face.
- Built-in benchmarks: latency, coding.
- Built-in reporters: JSON, CSV, Markdown.
- Dynamic prompt loading from YAML (`prompts/*.yaml`).
- Configuration via `configs/providers.yaml` and `configs/benchmark.yaml`.
- Environment-based API key resolution with `python-dotenv`.
