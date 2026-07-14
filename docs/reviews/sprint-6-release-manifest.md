# Release Manifest — v0.6.0

**Release Name:** Sprint 6 — Intelligent Routing & Automatic Model Selection  
**Release Date:** 2026-07-14  
**Version:** 0.6.0  
**Git Commit:** f7fc936b07e09029ff3451f3fd57fca1d76ef114  
**Git Tag:** v0.6.0  
**Baseline:** v0.5.0  

## Supported Platforms

- Linux (tested on Ubuntu-latest via CI)
- WSL2
- macOS and Windows via Python 3.13+ support

## Python Version

- Requires Python 3.13+
- CI uses Python 3.13

## Major Features

- Automatic model selection via strategy plugins
- LiteLLM routing config generation
- Fallback execution policy with circuit breaker
- Multi-provider parallel execution
- New reporters: routing, optimization, litellm_config
- New CLI commands: route, select, fallback, optimize, parallel, config generate-litellm
- Thread-safe HealthTracker and HistoryWriter
- CI workflow with test, lint, type-check

## Breaking Changes

None. All existing CLI commands and provider plugins preserved.

## Migration Notes

- No migration required from v0.5.0
- New behavior is opt-in via `configs/benchmark.yaml` routing section
- Parallel execution disabled by default

## Known Limitations

- SQLite history integration for historical performance selection not implemented in Sprint 6
- Context-window feasibility check omitted from Sprint 6
- Release automation workflow not implemented in Sprint 6
- README updated, but exhaustive user guide for new routing features pending

## Outstanding Technical Debt

- TD-4: Resolved (version default from pyproject)
- TD-5: Resolved (CI workflow added)
- TD-6: Deferred (release automation workflow)
- TD-9: Resolved (HealthTracker thread-safety)
- TD-10: Resolved (HistoryWriter serialization)
- Model alternation under fallback: Scheduled for Sprint 7
- Context-window feasibility check: Scheduled for Sprint 7
- SQLite history-driven selection: Scheduled for Sprint 7
