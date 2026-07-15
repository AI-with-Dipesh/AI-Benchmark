# Sprint 7 Release Notes

Release Version: 0.7.0
Sprint: 7
Release Date: 2026-07-15T07:05:55Z
Engineering Baseline: v0.6.0 -> v0.7.0

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

## Release Governance

- Architecture Freeze: Completed
- Quality Gates: Passed
- Formal Acceptance: Granted with registered technical debt (TD-Coverage-7)
- Repository Audit: Passed
- Release Snapshot: Created

## Technical Debt

- Overall coverage: 89%
- New Sprint 7 modules: 94-100%
- Deferred legacy modules per Sprint 7 Planning Report allowances
