# Changelog

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
