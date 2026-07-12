# Sprint 1 Documentation

## Goal

Build a benchmark engine that can benchmark at least one model from configuration loading through report generation without crashing.

## Scope

- Configuration loader with provider, weight, and prompt mappings.
- Environment variable resolution for API keys.
- Plugin-based provider initialization on demand.
- Dynamic prompt loading from `prompts/*.yaml`.
- Benchmarks: latency, coding.
- Reporters: JSON, CSV, Markdown.
- Click CLI with `benchmark run <provider> -m <model>` and `benchmark run main`.
- Graceful failure handling for missing keys, network errors, and invalid configuration.

## Acceptance Criteria

- `benchmark run main` executes end-to-end.
- Configuration loads correctly.
- Environment variables load.
- Provider initializes.
- Prompt loader works.
- Benchmark executes.
- Scores calculate correctly.
- Reports generate.
- No crashes.
- Errors are user-friendly.

## Status

Passed. Live connectivity depends on external provider availability; network failures are handled gracefully via `BenchmarkResult(status=\"error\")`.
