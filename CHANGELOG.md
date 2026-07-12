# Changelog

## [0.1.0] - 2026-07-12

### Added
- Initial release: AI-Benchmark Sprint 1.
- Plugin-based benchmark engine.
- Built-in providers: Ollama, NVIDIA, OpenRouter, Hugging Face, Gemini.
- Built-in benchmarks: latency, coding.
- Built-in reporters: JSON, CSV, Markdown.
- Dynamic prompt loading from YAML.
- `benchmark run main` support via defaults configuration.
- Graceful error handling for missing API keys, network failures, and invalid configs.

### Fixed
- YAML parsing errors return clean CLI messages.
- Prompt loader resolves paths outside `configs/`.
- Unused API key warnings removed for unselected providers.
