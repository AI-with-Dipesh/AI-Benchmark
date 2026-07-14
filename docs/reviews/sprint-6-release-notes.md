# Release Notes — v0.6.0

**Sprint:** 6  
**Theme:** Intelligent Routing & Automatic Model Selection  
**Release Date:** 2026-07-14

## Sprint Objectives Achieved

- LiteLLM-style routing configuration generation
- Automatic model selection for all benchmark categories
- Fallback strategies with retry/fallback separation
- Cost-optimized execution paths
- Multi-provider parallel execution with thread-safe boundaries
- Provider-specific execution reports

## Major New Capabilities

- Strategy plugin framework operational
- ModelSelector with 4 selection strategies
- ExecutionPolicy with circuit breaker
- ParallelExecutor with deterministic ordering
- 3 new reporters: routing, optimization, litellm_config
- 6 new CLI commands
- Thread-safe HealthTracker and HistoryWriter
- CI workflow with test, lint, type-check

## Architectural Improvements

- Strategy plugin extension point utilized
- Engine orchestration via delegation
- Reporter-only LiteLLM config generation
- PluginManager pluralization fix for STRATEGY

## Quality Improvements

- 89% overall coverage
- New code coverage 97-100%
- 234 tests passing, 6 skipped

## Testing Summary

- 3 new test files added
- No regressions detected

## Known Limitations

- History-driven model selection deferred
- Context-window feasibility check deferred
- Release automation workflow deferred

## Version

0.6.0
