# Changelog

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
