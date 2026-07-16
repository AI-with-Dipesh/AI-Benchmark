# Sprint 10 Technical Debt Register

**Sprint:** Sprint 10 – Version 1.2
**Baseline:** Version 1.0.0 (Frozen and Immutable)

## Active Technical Debt Items

| ID | Description | Priority | Origin Sprint | Recommended Sprint | Risk | Owner | Status |
|----|-------------|----------|---------------|-------------------|------|-------|--------|
| TD-Coverage-7 | Overall test coverage remains below the 95% long-term target due to uncovered legacy Sprint 1–3 modules. | High | Sprint 7 | Sprint 11+ | Low | TBD | Active Accepted |
| TD-ResourceWarnings-9 | Test suite may emit `ResourceWarning` from unclosed `sqlite3.Connection` objects during history helpers (`load_latest`, `load_run`, `_connect`). | Low | Sprint 9 | Sprint 11+ | Low | TBD | Accepted workaround |

### TD-Coverage-7 Remediation Plan
- Sprint 10: Add targeted tests for uncovered production paths (auth, auto-validation, config validation, execution policy, plugin manager, validation helpers). Target 94% rounded coverage achieved.
- Sprint 11+: Continue expanding legacy module tests until 95% reached.

### TD-ResourceWarnings-9 Evidence and Reclassification
- **Previous classification:** PyYAML C extension internals (superseded).
- **Current root cause:** SQLite connection lifecycle in `aibenchmark/app/history.py`. `_connect()`, `load_latest()`, and `load_run()` can leave connections unclosed under test teardown, surfacing `ResourceWarning: unclosed database`.
- **Mitigation:** `pyproject.toml` pytest configuration includes `filterwarnings = ["ignore::ResourceWarning"]`.
- **Rationale for acceptance:** The warnings do not affect runtime under standard execution; the suppression prevents noisy test output while a proper connection-lifecycle fix is deferred.
- **Remediation path:** Refactor history helpers to ensure deterministic connection closure; consider context-manager enforcement in `HistoryWriter`.

## Deferred Technical Debt
None.

## Retired Technical Debt
None.
