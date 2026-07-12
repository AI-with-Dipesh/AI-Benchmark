# Changelog

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

## [0.1.0] - 2026-07-12

### Added
- Initial release: AI-Benchmark Sprint 1.
- Plugin-based benchmark engine.
- Built-in providers: Ollama, NVIDIA, OpenRouter, Hugging Face, Gemini.
- Built-in benchmarks: latency, coding.
- Built-in reporters: JSON, CSV, Markdown.
- Dynamic prompt loading from YAML (`prompts/*.yaml`).
- Configuration via `configs/providers.yaml` and `configs/benchmark.yaml`.
- Environment-based API key resolution with `python-dotenv`.
